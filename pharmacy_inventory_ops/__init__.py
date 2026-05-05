from . import models
from . import wizard


def _post_init_force_avco(env):
    """Force all ir.default records for property_cost_method to 'average'."""
    env.cr.execute("""
        UPDATE ir_default
        SET json_value = '"average"'
        WHERE field_id IN (
            SELECT id FROM ir_model_fields
            WHERE name = 'property_cost_method'
              AND model = 'product.category'
        )
    """)
