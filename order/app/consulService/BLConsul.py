import consul
import dns.resolver
import logging
from consulService.config import Config

logger = logging.getLogger(__name__)

config = Config.get_instance()

# Consul instance
consul_instance = consul.Consul(
    host=config.CONSUL_HOST,
    port=config.CONSUL_PORT
)

# DNS resolver
consul_resolver = dns.resolver.Resolver(configure=False)
consul_resolver.port = config.CONSUL_DNS_PORT
consul_resolver.nameservers = [config.CONSUL_HOST]

# Store a variable as an example
consul_instance.kv.put("aas_example_variable", "aas_example_value")


def register_consul_service(cons=consul_instance, conf=config):
    """Register service in consul"""
    logger.debug(f"Registering {conf.SERVICE_NAME} service ({conf.SERVICE_ID})")
    cons.agent.service.register(
        name=conf.SERVICE_NAME,
        service_id=conf.SERVICE_ID,
        address=conf.IP,
        port=conf.PORT,
        tags=["python", "microservice", "aas"],
        check={
            "http": 'http://{host}:{port}/{service_name}/health'.format(
                host=conf.IP,
                port=conf.PORT,
                service_name=conf.SERVICE_NAME
            ),
            "interval": '10s'
        }
    )
    logger.info(f"Registered {conf.SERVICE_NAME} service ({conf.SERVICE_ID})")


def get_consul_service(service_name, consul_dns_resolver=consul_resolver):
    """Get service from consul"""
    ret = {
        "Address": None,
        "Port": None
    }
    try:
        #  srv_results = consul_dns_resolver.query("{}.service.consul".format(service_name), "srv")

        srv_results = consul_dns_resolver.resolve(
            "{}.service.consul".format(service_name),
            "srv"
        )  # SRV DNS query
        srv_list = srv_results.response.answer  # PORT - target_name relation
        a_list = srv_results.response.additional  # IP - target_name relation

        # DNS returns a list of replicas, supposedly sorted using Round Robin. We always get the 1st element: [0]
        srv_replica = srv_list[0][0]
        port = srv_replica.port
        target_name = srv_replica.target

        # From all the IPs, get the one with the chosen target_name
        for a in a_list:
            if a.name == target_name:
                ret['Address'] = a[0]
                ret['Port'] = port
                break

    except dns.exception.DNSException as e:
        logger.error("Could not get service url: {}".format(e))
    return ret


def get_consul_key_value_item(key, cons=consul_instance):
    """Get consul item value for the given key. It only works for string items!"""
    index, data = cons.kv.get(key)
    value = None
    if data and data['Value']:
        value = data['Value'].decode('utf-8')
    return key, value


def get_consul_service_catalog(cons=consul_instance):
    """List al consul services"""
    return cons.catalog.services()


def get_consul_service_replicas(cons=consul_instance):
    """Get all services including replicas"""
    return cons.agent.services()
