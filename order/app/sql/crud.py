# -*- coding: utf-8 -*-
"""Functions that interact with the database."""
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func
from sql.database import SessionLocal # pylint: disable=import-outside-toplevel
from routers.rabbitmq import publish_event, publish_command
from . import models
import json


# Generic functions #################################################################################
# READ
async def get_list(db: AsyncSession, model):
    """Retrieve a list of elements from database"""
    result = await db.execute(select(model))
    item_list = result.unique().scalars().all()
    return item_list


async def get_list_statement_result(db: AsyncSession, stmt):
    """Execute given statement and return list of items."""
    result = await db.execute(stmt)
    item_list = result.unique().scalars().all()
    return item_list


async def get_element_statement_result(db: AsyncSession, stmt):
    """Execute statement and return a single items"""
    result = await db.execute(stmt)
    item = result.scalar()
    return item


async def get_element_by_id(db: AsyncSession, model, element_id):
    """Retrieve any DB element by id."""
    if element_id is None:
        return None
    element = await db.get(model, element_id)
    return element


# DELETE
async def delete_element_by_id(db: AsyncSession, model, element_id):
    """Delete any DB element by id."""
    element = await get_element_by_id(db, model, element_id)
    if element is not None:
        await db.delete(element)
        await db.commit()
    return element


# Order functions ##################################################################################
async def get_orders_list(db: AsyncSession):
    """Load all the orders from the database."""
    stmt = select(models.Order)
    orders = await get_list_statement_result(db, stmt)
    return orders


async def get_order(db: AsyncSession, order_id):
    """Load an order from the database."""
    return await get_element_by_id(db, models.Order, order_id)


async def get_piece(db: AsyncSession, piece_id):
    """Load an piece from the database."""
    return await get_element_by_id(db, models.Piece, piece_id)


async def get_clients_orders(db: AsyncSession, client_id):
    """Load all the orders from the database."""
    stmt = select(models.Order).where(models.Order.id_client == client_id)
    orders = await get_list_statement_result(db, stmt)
    return orders


async def get_sagas_history_by_order_id(db: AsyncSession, id_order):
    """Load all the sagas history of certain order from the database."""
    stmt = select(models.SagasHistory).where(models.SagasHistory.id_order == id_order)
    sagas = await get_list_statement_result(db, stmt)
    return sagas


async def create_order(db: AsyncSession, order):
    """Persist a new order into the database."""
    movement = - float(order.number_of_pieces)
    if movement >= 0:
        raise Exception("You can't order that amount of pieces.")
    db_order = models.Order(
        number_of_pieces=order.number_of_pieces,
        description=order.description,
        id_client=order.id_client,
        status_order=models.Order.STATUS_DELIVERY_PENDING
    )
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    db_saga = SessionLocal()
    await create_sagas_history(db_saga, db_order.id_order, db_order.status_order)
    await db_saga.close()
    data = {
        "id_order": db_order.id_order,
        "id_client": db_order.id_client
    }
    message_body = json.dumps(data)
    routing_key = "delivery.check"
    await publish_command(message_body, routing_key)
    return db_order


async def change_order_status(db: AsyncSession, id, status):
    """Change order status in the database."""
    db_order = await get_order(db, id)
    db_order.status_order = status
    await db.commit()
    await db.refresh(db_order)
    return db_order


async def create_sagas_history(db: AsyncSession, id_order, status):
    """Persist a new sagas history into the database."""
    db_sagahistory = models.SagasHistory(
        id_order=id_order,
        status=status
    )
    db.add(db_sagahistory)
    await db.commit()
    await db.refresh(db_sagahistory)
    return db_sagahistory


async def get_sagas_history(db: AsyncSession, id_order):
    """Load sagas history from the database."""
    return await get_sagas_history_by_order_id(db, id_order)


async def create_piece(db: AsyncSession, piece):
    """Persist a new piece into the database."""
    db_piece = models.Piece(
        status_piece=piece.status_piece,
        id_order=piece.id_order
    )
    db.add(db_piece)
    await db.commit()
    await db.refresh(db_piece)
    data = {
        "id_order": db_piece.id_order,
        "id_piece": db_piece.id_piece
    }
    # Crear evento con nueva order, indicando ID de cliente y cantidad de piezas.
    message_body = json.dumps(data)
    routing_key = "piece.needed"
    await publish_event(message_body, routing_key)
    return db_piece


async def change_piece_status(db: AsyncSession, piece_id, status):
    """Change piece status in the database."""
    db_piece = await get_piece(db, piece_id)
    db_piece.status_piece = status
    db_piece.manufacturing_date = func.now()
    await db.commit()
    await db.refresh(db_piece)
    return db_piece


async def get_order_pieces(db: AsyncSession, order_id):
    """Load all the payments from the database."""
    stmt = select(models.Piece).where(models.Piece.id_order == order_id)
    pieces = await get_list_statement_result(db, stmt)
    return pieces
