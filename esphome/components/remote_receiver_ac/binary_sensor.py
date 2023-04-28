from esphome.components import binary_sensor
from ...esphome.components import remote_base_ac

DEPENDENCIES = ["remote_receiver_ac"]

CONFIG_SCHEMA = remote_base_ac.validate_binary_sensor

async def to_code(config):
    var = await remote_base_ac.build_binary_sensor(config)
    await binary_sensor.register_binary_sensor(var, config)
