import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import automation
from esphome.components import binary_sensor
from esphome.const import (
    CONF_DATA,
    CONF_TRIGGER_ID,
    CONF_NBITS,
    CONF_ADDRESS,
    CONF_COMMAND,
    CONF_CODE,
    CONF_PULSE_LENGTH,
    CONF_SYNC,
    CONF_ZERO,
    CONF_ONE,
    CONF_INVERTED,
    CONF_PROTOCOL,
    CONF_GROUP,
    CONF_DEVICE,
    CONF_STATE,
    CONF_CHANNEL,
    CONF_FAMILY,
    CONF_REPEAT,
    CONF_WAIT_TIME,
    CONF_TIMES,
    CONF_TYPE_ID,
    CONF_CARRIER_FREQUENCY,
    CONF_RC_CODE_1,
    CONF_RC_CODE_2,
    CONF_MAGNITUDE,
    CONF_WAND_ID,
    CONF_LEVEL,
)
from esphome.core import coroutine
from esphome.schema_extractors import SCHEMA_EXTRACT, schema_extractor
from esphome.util import Registry, SimpleRegistry

AUTO_LOAD = ["binary_sensor"]

CONF_RECEIVER_ID = "receiver_id"
CONF_TRANSMITTER_ID = "transmitter_id"

ns = remote_base_ns = cg.esphome_ns.namespace("remote_base_ac")
RemoteProtocol = ns.class_("RemoteProtocol")
RemoteReceiverListener = ns.class_("RemoteReceiverListener")
RemoteReceiverBinarySensorBase = ns.class_(
    "RemoteReceiverBinarySensorBase", binary_sensor.BinarySensor, cg.Component
)
RemoteReceiverTrigger = ns.class_(
    "RemoteReceiverTrigger", automation.Trigger, RemoteReceiverListener
)
RemoteTransmitterDumper = ns.class_("RemoteTransmitterDumper")
RemoteTransmitterActionBase = ns.class_(
    "RemoteTransmitterActionBase", automation.Action
)
RemoteReceiverBase = ns.class_("RemoteReceiverACBase")
RemoteTransmitterBase = ns.class_("RemoteTransmitterACBase")


def templatize(value):
    if isinstance(value, cv.Schema):
        value = value.schema
    ret = {}
    for key, val in value.items():
        ret[key] = cv.templatable(val)
    return cv.Schema(ret)


async def register_listener(var, config):
    receiver = await cg.get_variable(config[CONF_RECEIVER_ID])
    cg.add(receiver.register_listener(var))


def register_binary_sensor(name, type, schema):
    return BINARY_SENSOR_REGISTRY.register(name, type, schema)


def register_trigger(name, type, data_type):
    validator = automation.validate_automation(
        {
            cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(type),
            cv.Optional(CONF_RECEIVER_ID): cv.invalid(
                "This has been removed in ESPHome 2022.3.0 and the trigger attaches directly to the parent receiver."
            ),
        }
    )
    registerer = TRIGGER_REGISTRY.register(f"on_{name}", validator)

    def decorator(func):
        async def new_func(config):
            var = cg.new_Pvariable(config[CONF_TRIGGER_ID])
            await coroutine(func)(var, config)
            await automation.build_automation(var, [(data_type, "x")], config)
            return var

        return registerer(new_func)

    return decorator


def register_dumper(name, type):
    registerer = DUMPER_REGISTRY.register(name, type, {})

    def decorator(func):
        async def new_func(config, dumper_id):
            var = cg.new_Pvariable(dumper_id)
            await coroutine(func)(var, config)
            return var

        return registerer(new_func)

    return decorator


def validate_repeat(value):
    if isinstance(value, dict):
        return cv.Schema(
            {
                cv.Required(CONF_TIMES): cv.templatable(cv.positive_int),
                cv.Optional(CONF_WAIT_TIME, default="25ms"): cv.templatable(
                    cv.positive_time_period_microseconds
                ),
            }
        )(value)
    return validate_repeat({CONF_TIMES: value})


BASE_REMOTE_TRANSMITTER_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_TRANSMITTER_ID): cv.use_id(RemoteTransmitterBase),
        cv.Optional(CONF_REPEAT): validate_repeat,
    }
)


def register_action(name, type_, schema):
    validator = templatize(schema).extend(BASE_REMOTE_TRANSMITTER_SCHEMA)
    registerer = automation.register_action(
        f"remote_transmitter.transmit_{name}", type_, validator
    )

    def decorator(func):
        async def new_func(config, action_id, template_arg, args):
            transmitter = await cg.get_variable(config[CONF_TRANSMITTER_ID])
            var = cg.new_Pvariable(action_id, template_arg)
            cg.add(var.set_parent(transmitter))
            if CONF_REPEAT in config:
                conf = config[CONF_REPEAT]
                template_ = await cg.templatable(conf[CONF_TIMES], args, cg.uint32)
                cg.add(var.set_send_times(template_))
                template_ = await cg.templatable(conf[CONF_WAIT_TIME], args, cg.uint32)
                cg.add(var.set_send_wait(template_))
            await coroutine(func)(var, config, args)
            return var

        return registerer(new_func)

    return decorator


def declare_protocol(name):
    data = ns.struct(f"{name}Data")
    binary_sensor_ = ns.class_(f"{name}BinarySensor", RemoteReceiverBinarySensorBase)
    trigger = ns.class_(f"{name}Trigger", RemoteReceiverTrigger)
    action = ns.class_(f"{name}Action", RemoteTransmitterActionBase)
    dumper = ns.class_(f"{name}Dumper", RemoteTransmitterDumper)
    return data, binary_sensor_, trigger, action, dumper


BINARY_SENSOR_REGISTRY = Registry(
    binary_sensor.binary_sensor_schema().extend(
        {
            cv.GenerateID(CONF_RECEIVER_ID): cv.use_id(RemoteReceiverBase),
        }
    )
)
validate_binary_sensor = cv.validate_registry_entry(
    "remote receiver", BINARY_SENSOR_REGISTRY
)
TRIGGER_REGISTRY = SimpleRegistry()
DUMPER_REGISTRY = Registry(
    {
        cv.Optional(CONF_RECEIVER_ID): cv.invalid(
            "This has been removed in ESPHome 1.20.0 and the dumper attaches directly to the parent receiver."
        ),
    }
)


def validate_dumpers(value):
    if isinstance(value, str) and value.lower() == "all":
        return validate_dumpers(list(DUMPER_REGISTRY.keys()))
    return cv.validate_registry("dumper", DUMPER_REGISTRY)(value)


def validate_triggers(base_schema):
    assert isinstance(base_schema, cv.Schema)

    @schema_extractor("triggers")
    def validator(config):
        added_keys = {}
        for key, (_, valid) in TRIGGER_REGISTRY.items():
            added_keys[cv.Optional(key)] = valid
        new_schema = base_schema.extend(added_keys)

        if config == SCHEMA_EXTRACT:
            return new_schema
        return new_schema(config)

    return validator


async def build_binary_sensor(full_config):
    registry_entry, config = cg.extract_registry_entry_config(
        BINARY_SENSOR_REGISTRY, full_config
    )
    type_id = full_config[CONF_TYPE_ID]
    builder = registry_entry.coroutine_fun
    var = cg.new_Pvariable(type_id)
    await cg.register_component(var, full_config)
    await register_listener(var, full_config)
    await builder(var, config)
    return var


async def build_triggers(full_config):
    triggers = []
    for key in TRIGGER_REGISTRY:
        for config in full_config.get(key, []):
            func = TRIGGER_REGISTRY[key][0]
            triggers.append(await func(config))
    return triggers


async def build_dumpers(config):
    dumpers = []
    for conf in config:
        dumper = await cg.build_registry_entry(DUMPER_REGISTRY, conf)
        dumpers.append(dumper)
    return dumpers


# LG
LGData, LGBinarySensor, LGTrigger, LGAction, LGDumper = declare_protocol("LGAC")
LG_SCHEMA = cv.Schema(
    {
        cv.Required(CONF_DATA): cv.hex_uint32_t,
        cv.Optional(CONF_NBITS, default=28): cv.one_of(28, 32, int=True),
    }
)


@register_binary_sensor("lgac", LGBinarySensor, LG_SCHEMA)
def lg_binary_sensor(var, config):
    cg.add(
        var.set_data(
            cg.StructInitializer(
                LGData,
                ("data", config[CONF_DATA]),
                ("nbits", config[CONF_NBITS]),
            )
        )
    )


@register_trigger("lgac", LGTrigger, LGData)
def lg_trigger(var, config):
    pass


@register_dumper("lgac", LGDumper)
def lg_dumper(var, config):
    pass


@register_action("lgac", LGAction, LG_SCHEMA)
async def lg_action(var, config, args):
    template_ = await cg.templatable(config[CONF_DATA], args, cg.uint32)
    cg.add(var.set_data(template_))
    template_ = await cg.templatable(config[CONF_NBITS], args, cg.uint8)
    cg.add(var.set_nbits(template_))
