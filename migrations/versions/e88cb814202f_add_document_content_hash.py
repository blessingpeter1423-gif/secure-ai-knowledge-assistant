from pathlib import Path
import hashlib

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e88cb814202f"
down_revision = "35a3eeffe3aa"
branch_labels = None
depends_on = None


def calculate_file_hash(file_path: str) -> str:
    path = Path(file_path)

    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def upgrade() -> None:

    # Step 1:
    # Add the column temporarily as nullable because
    # existing documents do not have a hash yet.
    op.add_column(
        "documents",
        sa.Column(
            "content_hash",
            sa.String(length=64),
            nullable=True
        )
    )

    # Step 2:
    # Read existing documents and calculate their hashes.
    connection = op.get_bind()

    documents = connection.execute(
        sa.text(
            """
            SELECT id, file_path
            FROM documents
            """
        )
    ).fetchall()

    for document_id, file_path in documents:

        path = Path(file_path)

        if path.exists():
            content_hash = calculate_file_hash(
                file_path
            )

            connection.execute(
                sa.text(
                    """
                    UPDATE documents
                    SET content_hash = :content_hash
                    WHERE id = :document_id
                    """
                ),
                {
                    "content_hash": content_hash,
                    "document_id": document_id
                }
            )

    # Step 3:
    # Make sure every existing document received a hash.
    missing_hashes = connection.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM documents
            WHERE content_hash IS NULL
            """
        )
    ).scalar()

    if missing_hashes:
        raise RuntimeError(
            f"{missing_hashes} document(s) could not be assigned "
            "a content hash. Migration stopped."
        )

    # Step 4:
    # SQLite requires a table rebuild to change the column
    # from nullable=True to nullable=False.
    with op.batch_alter_table(
        "documents"
    ) as batch_op:

        batch_op.alter_column(
            "content_hash",
            existing_type=sa.String(length=64),
            nullable=False
        )


def downgrade() -> None:

    with op.batch_alter_table(
        "documents"
    ) as batch_op:

        batch_op.drop_column(
            "content_hash"
        )