# -*- coding: utf-8 -*-
from odoo.tools.translate import _
from odoo import http
from odoo import http
from odoo.http import request
import datetime
from datetime import datetime, date
from pytz import timezone, UTC
from dateutil.tz import tzlocal
# from tabulate import tabulate
import json
import sys
import yaml
import logging
_logger = logging.getLogger(__name__)

from werkzeug import urls
from werkzeug.wsgi import wrap_file

import re
import math

def sql_ids_stock_move_line():
    query = """SELECT sml1.id FROM stock_move_line sml1				
                JOIN 
                (
                select lot_id, MAX(date) AS MAXDATE from stock_move_line 
                    where lot_id is not null
                    group by lot_id
                ) sml2
				
                ON sml1.lot_id = sml2.lot_id
                AND sml1.date = sml2.MAXDATE
				AND sml1.state='done'
                ORDER BY sml1.date
                """
    request.cr.execute(query)
    res = [l for l in request.cr.fetchall()]
    return res or [0]

def as_convert(txt,digits,is_number=False,is_rut=False):
    if is_number:
        if is_rut:
            index = txt.find('-')
            if index == -1 or re.sub("\D", "", txt[:txt.find('-')]) == '':
                return 0
            else:
                num = re.sub("\D", "", txt[:txt.find('-')])
                return int(num[0:digits])
        num = re.sub("\D", "", txt)
        if num == '':
            return 0
        return int(num[0:digits])
    else:
        return txt[0:digits]


class webservice(http.Controller):
    # @http.route('/webservice/stock1', auth='public', methods=['POST'], type="json", csrf=False)
    @http.route('/webservice/stock1', auth='public', type="http")
    def stock1(self, **post):
        ids = sql_ids_stock_move_line()
        stock_move_model = request.env['stock.move.line']
        stock_move_ids = stock_move_model.sudo().search([('id','in',ids)])
        user = request.env['res.users']
        tz = user.sudo().search([('login','=','admin')]).tz

        json_dict = []
        for stock_move in stock_move_ids:
            fecha_asignacion=stock_move.date.astimezone(timezone(tz))
            if 'x_studio_fecha_asignacin' in request.env['stock.move.line']._fields:
            #if 'x_studio_field_BUaym' in request.env['stock.move']._fields:
                if stock_move.x_studio_fecha_asignacin:
                    fecha_asignacion = stock_move.x_studio_fecha_asignacin.astimezone(timezone(tz))
            categ_id = stock_move.product_id.product_tmpl_id.categ_id.x_studio_cod_categora_1 if 'x_studio_cod_categora_1' in request.env['product.category']._fields else ''
            procesador_at = stock_move.product_id.product_tmpl_id.x_studio_field_E6Mvt.x_name if 'x_studio_field_E6Mvt' in request.env['product.template']._fields else ''
            velocidad_at = stock_move.product_id.product_tmpl_id.x_studio_field_q1N0G.x_name if 'x_studio_field_q1N0G' in request.env['product.template']._fields else ''
            memoria_at = stock_move.product_id.product_tmpl_id.x_studio_field_lNFQG.x_name if 'x_studio_field_lNFQG' in request.env['product.template']._fields else ''
            hdd_at = stock_move.product_id.product_tmpl_id.x_studio_field_WRME0.x_name if 'x_studio_field_WRME0' in request.env['product.template']._fields else ''
            costo_compra_at = stock_move.lot_id.purchase_order_ids.amount_total if stock_move.lot_id.purchase_order_ids else stock_move.lot_id.x_studio_costo_compra
            fecha_compra_at = stock_move.lot_id.purchase_order_ids.date_order if stock_move.lot_id.purchase_order_ids else stock_move.lot_id.x_studio_field_6Pp3S
            
            sm = {
                    "reference": stock_move.reference,
                    "lote": as_convert(str(stock_move.lot_id.name) or "",9,True), #Lote/N° de serie
                    "categ_id": as_convert(str(categ_id) or "",6,True), #cod categoria
                    "categoria": as_convert(stock_move.product_id.product_tmpl_id.categ_id.name or "",30), #categoria
                    "rut": as_convert(str(stock_move.location_dest_id.barcode) or "",9,True,True), #rut (sin digito verificador)
                    "usuario": as_convert(stock_move.location_dest_id.name or "",50), #Nombre usuario
                    "codigo_marca": as_convert(str(stock_move.product_id.product_tmpl_id.x_studio_field_To4X6.x_cod_marcas_de_at) or "",6,True), #cod Marca
                    "marca": as_convert(stock_move.product_id.product_tmpl_id.x_studio_field_To4X6.x_name or "",20),#Marca
                    "modelo": as_convert(stock_move.product_id.product_tmpl_id.x_studio_field_5Bj0L.x_name or "",30), #Modelo
                    "referencia_proveedor": as_convert(stock_move.lot_id.ref or "",30), #referencia (proveedor)
                    "procesador_at": as_convert(procesador_at or "",20), #Procesador_at
                    "velocidad_at": as_convert(velocidad_at or "",10), #Velocidad_at
                    "memoria_at": as_convert(memoria_at or "",10), #Memoria_at
                    "hdd_at": as_convert(hdd_at or "",10), #Hdd_at
                    "costo_compra_at": as_convert(str(costo_compra_at) or "",9,True), #Costo compra AT
                    "proveedor": as_convert(stock_move.lot_id.purchase_order_ids[0].partner_id.name if stock_move.lot_id.purchase_order_ids else "",30),#proveedor
                    "N_factura": as_convert(str(stock_move.lot_id.x_studio_n_factura) or "",9,True),#N_factura
                    "fecha_compra_at": as_convert(str(fecha_compra_at) or "",10),#fecha compra AT
                    "fecha_asignacion": as_convert(str(fecha_asignacion) or "",10) #Fecha asignacion                    
                }
            json_dict.append(sm)
        return json.dumps(json_dict)

    @http.route('/webservice/stock2', auth='public', type="http")
    def stock2(self, **post):
        el_token = post.get('token') or 'sin_token'
        current_user = request.env['res.users'].sudo().search([('token', '=', el_token)])        
        if not current_user:
            return json.dumps({'error': _('Token Invalido')})
        else:
            limit = int(post['limit']) if post.get('limit') else 0
            offset = int(post['offset']) if post.get('offset') else 0
            ids = sql_ids_stock_move_line()
            stock_move_model = request.env['stock.move.line']

            stock_move_ids = stock_move_model.sudo().search([('id','in',ids)], limit=limit, offset=offset)
            tz = current_user.sudo().search([('login','=','admin')]).tz

            # stock_move_ids = stock_move_model.sudo().search([('stock_move.lot_id.name','in',request.params['lote'])],limit=500)

            json_dict = []
            for stock_move in stock_move_ids:
                fecha_asignacion=stock_move.date.astimezone(timezone(tz))
                if 'x_studio_fecha_asignacin' in request.env['stock.move.line']._fields:
                #if 'x_studio_field_BUaym' in request.env['stock.move']._fields:
                    if stock_move.x_studio_fecha_asignacin:
                        fecha_asignacion = stock_move.x_studio_fecha_asignacin.astimezone(timezone(tz))
                categ_id = stock_move.product_id.product_tmpl_id.categ_id.x_studio_cod_categora_1 if 'x_studio_cod_categora_1' in request.env['product.category']._fields else ''
                procesador_at = stock_move.product_id.product_tmpl_id.x_studio_field_E6Mvt.x_name if 'x_studio_field_E6Mvt' in request.env['product.template']._fields else ''
                velocidad_at = stock_move.product_id.product_tmpl_id.x_studio_field_q1N0G.x_name if 'x_studio_field_q1N0G' in request.env['product.template']._fields else ''
                memoria_at = stock_move.product_id.product_tmpl_id.x_studio_field_lNFQG.x_name if 'x_studio_field_lNFQG' in request.env['product.template']._fields else ''
                hdd_at = stock_move.product_id.product_tmpl_id.x_studio_field_WRME0.x_name if 'x_studio_field_WRME0' in request.env['product.template']._fields else ''
                costo_compra_at = stock_move.lot_id.purchase_order_ids.amount_total if stock_move.lot_id.purchase_order_ids else stock_move.lot_id.x_studio_costo_compra
                fecha_compra_at = stock_move.lot_id.purchase_order_ids.date_order if stock_move.lot_id.purchase_order_ids else stock_move.lot_id.x_studio_field_6Pp3S
                
                sm = {
                        "reference": stock_move.reference,
                        "lote": as_convert(str(stock_move.lot_id.name) or "",9,True), #Lote/N° de serie
                        "categ_id": as_convert(str(categ_id) or "",6,True), #cod categoria
                        "categoria": as_convert(stock_move.product_id.product_tmpl_id.categ_id.name or "",30), #categoria
                        "rut": as_convert(str(stock_move.location_dest_id.barcode) or "",9,True,True), #rut (sin digito verificador)
                        "usuario": as_convert(stock_move.location_dest_id.name or "",50), #Nombre usuario
                        "codigo_marca": as_convert(str(stock_move.product_id.product_tmpl_id.x_studio_field_To4X6.x_cod_marcas_de_at) or "",6,True), #cod Marca
                        "marca": as_convert(stock_move.product_id.product_tmpl_id.x_studio_field_To4X6.x_name or "",20),#Marca
                        "modelo": as_convert(stock_move.product_id.product_tmpl_id.x_studio_field_5Bj0L.x_name or "",30), #Modelo
                        "referencia_proveedor": as_convert(stock_move.lot_id.ref or "",30), #referencia (proveedor)
                        "procesador_at": as_convert(procesador_at or "",20), #Procesador_at
                        "velocidad_at": as_convert(velocidad_at or "",10), #Velocidad_at
                        "memoria_at": as_convert(memoria_at or "",10), #Memoria_at
                        "hdd_at": as_convert(hdd_at or "",10), #Hdd_at
                        "costo_compra_at": as_convert(str(costo_compra_at) or "",9,True), #Costo compra AT
                        "proveedor": as_convert(stock_move.lot_id.purchase_order_ids[0].partner_id.name if stock_move.lot_id.purchase_order_ids else "",30),#proveedor
                        "N_factura": as_convert(str(stock_move.lot_id.x_studio_n_factura) or "",9,True),#N_factura
                        "fecha_compra_at": as_convert(str(fecha_compra_at) or "",10),#fecha compra AT
                        "fecha_asignacion": as_convert(str(fecha_asignacion) or "",10) #Fecha asignacion                    
                    }
                json_dict.append(sm)
            return json.dumps(json_dict)

    @http.route('/webservice/stock3', auth='public', type="http")
    def stock3(self, **post):
        ids = sql_ids_stock_move_line()
        stock_move_model = request.env['stock.move.line']
        stock_move_ids = stock_move_model.sudo().search([('id','in',ids)])
        user = request.env['res.users']
        tz = user.sudo().search([('login','=','admin')]).tz

        json_dict = []
        for stock_move in stock_move_ids:
            fecha_asignacion=stock_move.date.astimezone(timezone(tz))
            if 'x_studio_fecha_asignacin' in request.env['stock.move.line']._fields:
            #if 'x_studio_field_BUaym' in request.env['stock.move']._fields:
                if stock_move.x_studio_fecha_asignacin:
                    fecha_asignacion = stock_move.x_studio_fecha_asignacin.astimezone(timezone(tz))
            categ_id = stock_move.product_id.product_tmpl_id.categ_id.x_studio_cod_categora_1 if 'x_studio_cod_categora_1' in request.env['product.category']._fields else ''
            procesador_at = stock_move.product_id.product_tmpl_id.x_studio_field_E6Mvt.x_name if 'x_studio_field_E6Mvt' in request.env['product.template']._fields else ''
            velocidad_at = stock_move.product_id.product_tmpl_id.x_studio_field_q1N0G.x_name if 'x_studio_field_q1N0G' in request.env['product.template']._fields else ''
            memoria_at = stock_move.product_id.product_tmpl_id.x_studio_field_lNFQG.x_name if 'x_studio_field_lNFQG' in request.env['product.template']._fields else ''
            hdd_at = stock_move.product_id.product_tmpl_id.x_studio_field_WRME0.x_name if 'x_studio_field_WRME0' in request.env['product.template']._fields else ''
            costo_compra_at = stock_move.lot_id.purchase_order_ids.amount_total if stock_move.lot_id.purchase_order_ids else stock_move.lot_id.x_studio_costo_compra
            fecha_compra_at = stock_move.lot_id.purchase_order_ids.date_order if stock_move.lot_id.purchase_order_ids else stock_move.lot_id.x_studio_field_6Pp3S
            
            sm = {
                    "reference": stock_move.reference,
                    "lote": as_convert(str(stock_move.lot_id.name) or "",9,True), #Lote/N° de serie
                    "categ_id": as_convert(categ_id,6,True), #cod categoria
                    "categoria": as_convert(stock_move.product_id.product_tmpl_id.categ_id.name or "",30), #categoria
                    "rut": as_convert(str(stock_move.location_dest_id.barcode) or "",9,True,True), #rut (sin digito verificador)
                    "usuario": as_convert(stock_move.location_dest_id.name or "",50), #Nombre usuario
                    "codigo_marca": as_convert(str(stock_move.product_id.product_tmpl_id.x_studio_field_To4X6.x_cod_marcas_de_at) or "",6,True), #cod Marca
                    "marca": as_convert(stock_move.product_id.product_tmpl_id.x_studio_field_To4X6.x_name or "",20),#Marca
                    "modelo": as_convert(stock_move.product_id.product_tmpl_id.x_studio_field_5Bj0L.x_name or "",30), #Modelo
                    "referencia_proveedor": as_convert(stock_move.lot_id.ref or "",30), #referencia (proveedor)
                    "procesador_at": as_convert(procesador_at or "",20), #Procesador_at
                    "velocidad_at": as_convert(velocidad_at or "",10), #Velocidad_at
                    "memoria_at": as_convert(memoria_at or "",10), #Memoria_at
                    "hdd_at": as_convert(hdd_at or "",10), #Hdd_at
                    "costo_compra_at": as_convert(str(costo_compra_at) or "",9,True), #Costo compra AT
                    "proveedor": as_convert(stock_move.lot_id.purchase_order_ids[0].partner_id.name if stock_move.lot_id.purchase_order_ids else "",30),#proveedor
                    "N_factura": as_convert(str(stock_move.lot_id.x_studio_n_factura) or "",9,True),#N_factura
                    "fecha_compra_at": as_convert(str(fecha_compra_at) or "",10),#fecha compra AT
                    "fecha_asignacion": as_convert(str(fecha_asignacion) or "",10) #Fecha asignacion                    
                }
            json_dict.append(sm)
        return json.dumps(json_dict)

    @http.route(['/webservice/token',], auth="public", type="http")
    def token(self, **post):
        """
            Para autenticar se deben enviar usuario y password
            servidor.com:8069/webservice/token?login=admin&password=admin
        """
        res = {}
        try:
            uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
            if uid:
                user = request.env['res.users'].sudo().browse(uid)
                token = user.get_user_access_token()
                user.token = token
                res['token'] = token
                request.session.logout()
            else:
                res['error'] = "Login o Password erroneo"
            return json.dumps(res)
        except:
            res['error'] = "Envia login y password"
            return json.dumps(res)