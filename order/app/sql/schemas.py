# -*- coding: utf-8 -*-
"""Classes for Request/Response schema definitions."""
# pylint: disable=too-few-public-methods
from typing import List, Optional
from pydantic import BaseModel, Field  # pylint: disable=no-name-in-module
from datetime import datetime


class Message(BaseModel):
    """Message schema definition."""
    detail: Optional[str] = Field(example="error or success message")


class OrderBase(BaseModel):
    """Order base schema definition."""
    number_of_pieces: int = Field(
        description="Number of pieces to manufacture for the new order.",
        default=None,
        example=10
    )
    description: str = Field(
        description="Human readable description for the order.",
        default="No description",
        example="CompanyX order on 2022-01-20"
    )
    id_client: int = Field(
        description="Identifier of the client.",
        default=None,
        example=1
    )


class Order(OrderBase):
    """Order schema definition."""
    id_order: int = Field(
        description="Primary key/identifier of the order.",
        default=None,
        example=1
    )
    status_order: str = Field(
        description="Current status of the order.",
        default="Created",
        example="Finished"
    )

    class Config:
        """ORM configuration."""
        orm_mode = True


class OrderPost(OrderBase):
    """Schema definition to create a new order."""


class PieceBase(BaseModel):
    """Piece base schema definition."""
    
    id_order: int = Field(description="Order where the piece belongs to.")
    
    manufacturing_date: Optional[datetime] = Field(
        description="Date when piece has been manufactured.",
        example="2022-07-22T17:32:32.193211"
    )
    status_piece: str = Field(
        description="Current status of the piece.",
        default="Queued",
        example="Manufactured"
    )


class Piece(PieceBase):
    """Piece schema definition."""
    id_piece: int = Field(
        description="Piece identifier (Primary key).",
        example="1"
    )

    class Config:
        """ORM configuration."""
        orm_mode = True


class SagasHistoryBase(BaseModel):
    """Sagas history base schema definition."""
    id: int = Field()
    id_order: int = Field()
    status: str = Field()
