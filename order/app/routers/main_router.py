# -*- coding: utf-8 -*-
"""FastAPI router definitions."""
import logging
from typing import List
from fastapi import APIRouter, Depends, status, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies import get_db
from sql import crud, schemas
from routers import security
from routers.router_utils import raise_and_log_error
from routers import rabbitmq_publish_logs
import json

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/order/health",
    summary="Health check endpoint",
    response_model=schemas.Message,
)
async def health_check():
    """Endpoint to check if everything started correctly."""
    logger.debug("GET '/order/health' endpoint called.")
    if await security.isTherePublicKey():
        return {"detail": "Service Healthy."}
    else:
        raise_and_log_error(logger, status.HTTP_503_SERVICE_UNAVAILABLE, "Service Unavailable.")


@router.post(
    "/order",
    response_model=schemas.Order,
    summary="Create single order",
    status_code=status.HTTP_201_CREATED,
    tags=["Order"]
)
async def create_order(
        order_schema: schemas.OrderPost,
        db: AsyncSession = Depends(get_db),
        token: str = Header(..., description="JWT Token in the Header")
):
    """Create single order endpoint."""
    logger.debug("POST '/order' endpoint called.")
    try:
        #decodificar el token
        payload = security.decode_token(token)
        # validar fecha expiración del token
        is_expirated = security.validar_fecha_expiracion(payload)
        if(is_expirated):
            data = {
                "message": "ERROR - Token expired, log in again"
            }
            message_body = json.dumps(data)
            routing_key = "order.main_router_create_order.error"
            await rabbitmq_publish_logs.publish_log(message_body, routing_key)
            raise_and_log_error(logger, status.HTTP_409_CONFLICT, f"The token is expired, please log in again")
        else:
            order_schema.id_client = payload["id_client"]
            db_order = await crud.create_order(db, order_schema)
            data = {
                "message": "INFO - Order created"
            }
            message_body = json.dumps(data)
            routing_key = "order.main_router_create_order.info"
            await rabbitmq_publish_logs.publish_log(message_body, routing_key)
            return db_order
    except Exception as exc:  # @ToDo: To broad exception
        data = {
            "message": "ERROR - Error creating the order"
        }
        message_body = json.dumps(data)
        routing_key = "order.main_router_create_order.error"
        await rabbitmq_publish_logs.publish_log(message_body, routing_key)
        raise_and_log_error(logger, status.HTTP_409_CONFLICT, f"Error creating order: {exc}")



@router.get(
    "/order",
    summary="Retrieve single order by id",
    responses={
        status.HTTP_200_OK: {
            "model": schemas.Order,
            "description": "Requested Order."
        },
        status.HTTP_404_NOT_FOUND: {
            "model": schemas.Message, "description": "Order not found"
        }
    },
    tags=['Order']
)
async def get_single_order(
        order_id: int = Query(None, description="Order ID"),
        client_id: int = Query(None, description="Client ID"),
        db: AsyncSession = Depends(get_db),
        token: str = Header(..., description="JWT Token in the Header")
):
    """Retrieve single order by id"""
    logger.debug("GET '/order' endpoint called.", order_id)

    if order_id is None and client_id is None:
        try:
            #decodificar el token
            payload = security.decode_token(token)
            # validar fecha expiración del token
            is_expirated = security.validar_fecha_expiracion(payload)
            if(is_expirated):
                data = {
                    "message": "ERROR - Token expired, log in again"
                }
                message_body = json.dumps(data)
                routing_key = "order.main_router_get_order_list.error"
                await rabbitmq_publish_logs.publish_log(message_body, routing_key)
                raise_and_log_error(logger, status.HTTP_409_CONFLICT, f"The token is expired, please log in again")
            else:
                es_admin = security.validar_es_admin(payload)
                if(es_admin):
                    order_list = await crud.get_orders_list(db)
                    data = {
                        "message": "INFO - Order list obtained"
                    }
                    message_body = json.dumps(data)
                    routing_key = "order.main_router_get_order_list.info"
                    await rabbitmq_publish_logs.publish_log(message_body, routing_key)
                    return order_list
                else:
                    data = {
                        "message": "ERROR - You don't have permissions"
                    }
                    message_body = json.dumps(data)
                    routing_key = "order.main_router_get_order_list.error"
                    await rabbitmq_publish_logs.publish_log(message_body, routing_key)
                    raise_and_log_error(logger, status.HTTP_409_CONFLICT, f"You don't have permissions")
        except Exception as exc:  # @ToDo: To broad exception
            data = {
                "message": "ERROR - Error obtaining order list"
            }
            message_body = json.dumps(data)
            routing_key = "order.main_router_get_order_list.error"
            await rabbitmq_publish_logs.publish_log(message_body, routing_key)
            raise_and_log_error(logger, status.HTTP_409_CONFLICT, f"Error obtaining order list: {exc}")

    if order_id is not None and client_id is None:
        try:
            """Retrieve order list"""
            #decodificar el token
            payload = security.decode_token(token)
            # validar fecha expiración del token
            is_expirated = security.validar_fecha_expiracion(payload)
            if(is_expirated):
                data = {
                    "message": "ERROR - Token expired, log in again"
                }
                message_body = json.dumps(data)
                routing_key = "order.main_router_get_single_order.error"
                await rabbitmq_publish_logs.publish_log(message_body, routing_key)
                raise_and_log_error(logger, status.HTTP_409_CONFLICT, f"The token is expired, please log in again")
            else:
                es_admin = security.validar_es_admin(payload)
                client_id = payload["id_client"]
                order = await crud.get_order(db, order_id)
                if(es_admin==False and order.id_client!=client_id):
                    data = {
                        "message": "ERROR - You don't have permissions"
                    }
                    message_body = json.dumps(data)
                    routing_key = "order.main_router_get_single_order.error"
                    await rabbitmq_publish_logs.publish_log(message_body, routing_key)
                    raise_and_log_error(logger, status.HTTP_409_CONFLICT, f"You don't have permissions")
            if not order:
                data = {
                    "message": "ERROR - {order_id} Order not found"
                }
                message_body = json.dumps(data)
                routing_key = "order.main_router_get_single_order.error"
                await rabbitmq_publish_logs.publish_log(message_body, routing_key)
                raise_and_log_error(logger, status.HTTP_404_NOT_FOUND, f"Order {order_id} not found")
            data = {
                "message": "INFO - Order obtained"
            }
            message_body = json.dumps(data)
            routing_key = "order.main_router_get_single_order.info"
            await rabbitmq_publish_logs.publish_log(message_body, routing_key)
            return order
        except Exception as exc:  # @ToDo: To broad exception
            data = {
                "message": "ERROR - Error obtaining the order"
            }
            message_body = json.dumps(data)
            routing_key = "order.main_router_get_single_order.error"
            await rabbitmq_publish_logs.publish_log(message_body, routing_key)
            raise_and_log_error(logger, status.HTTP_409_CONFLICT, f"Error obtaining order: {exc}")

    if order_id is None and client_id is not None:
        payload = security.decode_token(token)
        # validar fecha expiración del token
        is_expirated = security.validar_fecha_expiracion(payload)
        if(is_expirated):
            data = {
                "message": "ERROR - Token expired, log in again"
            }
            message_body = json.dumps(data)
            routing_key = "order.main_router_get_single_client.error"
            await rabbitmq_publish_logs.publish_log(message_body, routing_key)
            raise_and_log_error(logger, status.HTTP_409_CONFLICT, f"The token is expired, please log in again")
        else:
            es_admin = security.validar_es_admin(payload)
            client_id_token = payload["id_client"]
            if(es_admin==False and client_id!=client_id_token):
                data = {
                    "message": "ERROR - You don't have permissions"
                }
                message_body = json.dumps(data)
                routing_key = "order.main_router_get_single_client.error"
                await rabbitmq_publish_logs.publish_log(message_body, routing_key)
                raise_and_log_error(logger, status.HTTP_409_CONFLICT, f"You don't have permissions")
        orders = await crud.get_clients_orders(db, client_id)
        if not orders:
            data = {
                "message": "ERROR - Clinet {client_id}'s orders not found"
            }
            message_body = json.dumps(data)
            routing_key = "order.main_router_get_single_client.error"
            await rabbitmq_publish_logs.publish_log(message_body, routing_key)
            raise_and_log_error(logger, status.HTTP_404_NOT_FOUND, f"Client {client_id}'s orders not found")
        data = {
            "message": "INFO - Orders of client {cliend_id} obtained"
        }
        message_body = json.dumps(data)
        routing_key = "order.main_router_get_single_client.info"
        await rabbitmq_publish_logs.publish_log(message_body, routing_key)
        return orders

## Cambiar endpoint
# @router.get(
#     "/order/client/{client_id}",
#     summary="Retrieve client's orders by id",
#     responses={
#         status.HTTP_200_OK: {
#             "model": schemas.Order,
#             "description": "Requested Orders."
#         },
#         status.HTTP_404_NOT_FOUND: {
#             "model": schemas.Message, "description": "Orders not found"
#         }
#     },
#     tags=['Orders'],
# )
# async def get_single_client(
#         client_id: int,
#         db: AsyncSession = Depends(get_db),
#         token: str = Header(..., description="JWT Token in the Header")
# ):
#     """Retrieve client's orders by id"""
#     logger.debug("GET '/order/client/%i' endpoint called.", client_id)
#     payload = security.decode_token(token)
#     # validar fecha expiración del token
#     is_expirated = security.validar_fecha_expiracion(payload)
#     if(is_expirated):
#         data = {
#             "message": "ERROR - Token expired, log in again"
#         }
#         message_body = json.dumps(data)
#         routing_key = "order.main_router_get_single_client.error"
#         await rabbitmq_publish_logs.publish_log(message_body, routing_key)
#         raise_and_log_error(logger, status.HTTP_409_CONFLICT, f"The token is expired, please log in again")
#     else:
#         es_admin = security.validar_es_admin(payload)
#         client_id_token = payload["id_client"]
#         if(es_admin==False and client_id!=client_id_token):
#             data = {
#                 "message": "ERROR - You don't have permissions"
#             }
#             message_body = json.dumps(data)
#             routing_key = "order.main_router_get_single_client.error"
#             await rabbitmq_publish_logs.publish_log(message_body, routing_key)
#             raise_and_log_error(logger, status.HTTP_409_CONFLICT, f"You don't have permissions")
#     orders = await crud.get_clients_orders(db, client_id)
#     if not orders:
#         data = {
#             "message": "ERROR - Clinet {client_id}'s orders not found"
#         }
#         message_body = json.dumps(data)
#         routing_key = "order.main_router_get_single_client.error"
#         await rabbitmq_publish_logs.publish_log(message_body, routing_key)
#         raise_and_log_error(logger, status.HTTP_404_NOT_FOUND, f"Client {client_id}'s orders not found")
#     data = {
#         "message": "INFO - Orders of client {cliend_id} obtained"
#     }
#     message_body = json.dumps(data)
#     routing_key = "order.main_router_get_single_client.info"
#     await rabbitmq_publish_logs.publish_log(message_body, routing_key)
#     return orders


@router.get(
    "/order/sagashistory",
    summary="Retrieve sagas history of a certain order",
    responses={
        status.HTTP_200_OK: {
            "model": schemas.SagasHistoryBase,
            "description": "Requested sagas history."
        },
        status.HTTP_404_NOT_FOUND: {
            "model": schemas.Message, "description": "Sagas history not found"
        }
    },
    tags=['Order']
)
async def get_sagas_history(
        order_id: int = Query(..., description="Order ID"),
        db: AsyncSession = Depends(get_db),
        token: str = Header(..., description="JWT Token in the Header")
):
    """Retrieve sagas history"""
    logger.debug("GET '/order/sagashistory/%i' endpoint called.", order_id)
    payload = security.decode_token(token)
    # validar fecha expiración del token
    is_expirated = security.validar_fecha_expiracion(payload)
    if(is_expirated):
        data = {
            "message": "ERROR - Token expired, log in again"
        }
        message_body = json.dumps(data)
        routing_key = "order.main_router_get_sagas_history.error"
        await rabbitmq_publish_logs.publish_log(message_body, routing_key)
        raise_and_log_error(logger, status.HTTP_409_CONFLICT, f"The token is expired, please log in again")
    else:
        es_admin = security.validar_es_admin(payload)
        if(es_admin==False):
            data = {
                "message": "ERROR - You don't have permissions"
            }
            message_body = json.dumps(data)
            routing_key = "order.main_router_get_sagas_history.error"
            await rabbitmq_publish_logs.publish_log(message_body, routing_key)
            raise_and_log_error(logger, status.HTTP_409_CONFLICT, f"You don't have permissions")
    logs = await crud.get_sagas_history(db, order_id)
    if not logs:
        data = {
            "message": "ERROR - Logs not found"
        }
        message_body = json.dumps(data)
        routing_key = "order.main_router_get_sagas_history.error"
        await rabbitmq_publish_logs.publish_log(message_body, routing_key)
        raise_and_log_error(logger, status.HTTP_404_NOT_FOUND)
    data = {
        "message": "INFO - Log obtained"
    }
    message_body = json.dumps(data)
    routing_key = "order.main_router_get_sagas_history.info"
    await rabbitmq_publish_logs.publish_log(message_body, routing_key)
    return logs
