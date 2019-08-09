# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_utils, float_compare    
from datetime import datetime, timedelta, date

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def write(self, vals):
        """ Through the interface, we allow users to change the charateristics of a move line. If a
        quantity has been reserved for this move line, we impact the reservation directly to free
        the old quants and allocate the new ones.
        """
        res = super(StockMoveLine, self).write(vals)

        #Se llena fecha asignada si corresponde a una fecha asignada en un "Ajuste de inventario"
        for move in self:            
            sil_obj = self.env['stock.inventory.line'].sudo().search([('inventory_id','=',move.move_id.inventory_id.id),('product_id','=',move.product_id.id),('prod_lot_id','=',move.lot_id.id)],limit=1,order='id desc')
            if sil_obj:
                if sil_obj.x_studio_fecha_asignacin:
                    self._cr.execute("""
                        UPDATE 
                            stock_move_line 
                        SET 
                            x_studio_fecha_asignacin ='%s' 
                        WHERE
                            product_id = %s
                            and lot_id = %s
                            """ % (
                            (datetime.strptime(fields.Datetime.to_string(sil_obj.x_studio_fecha_asignacin), '%Y-%m-%d %H:%M:%S')+ timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S'),
                            move.product_id.id,
                            move.lot_id.id
                            ) )

        return res