"""Book endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from studying_light.api.v1.schemas import BookCreate, BookOut, BookUpdate
from studying_light.db.models.book import Book
from studying_light.db.session import get_session

router: APIRouter = APIRouter()


@router.get("/books")
def list_books(session: Session = Depends(get_session)) -> list[BookOut]:
    """List all books."""
    books = session.execute(select(Book).order_by(Book.id)).scalars().all()
    return [BookOut.model_validate(book) for book in books]


@router.post("/books", status_code=status.HTTP_201_CREATED)
def create_book(payload: BookCreate, session: Session = Depends(get_session)) -> BookOut:
    """Create a new book."""
    book = Book(title=payload.title, author=payload.author, status="active")
    session.add(book)
    session.commit()
    session.refresh(book)
    return BookOut.model_validate(book)


@router.patch("/books/{book_id}")
def update_book(
    book_id: int,
    payload: BookUpdate,
    session: Session = Depends(get_session),
) -> BookOut:
    """Update an existing book."""
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    status_value = updates.get("status")
    if status_value and status_value not in {"active", "archived"}:
        raise HTTPException(status_code=422, detail="Invalid status value")

    for key, value in updates.items():
        setattr(book, key, value)

    session.commit()
    session.refresh(book)
    return BookOut.model_validate(book)


@router.delete("/books/{book_id}")
def delete_book(book_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    """Delete a book."""
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    session.delete(book)
    session.commit()
    return {"status": "deleted"}
