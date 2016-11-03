import httplib
import json
import subprocess

import requests

DOCKER_NETWORK = 'couchdb2_cluster_network'
DOCKER_CREATE_NETWORK = 'docker network create --subnet=172.18.0.0/16 {}'.format(DOCKER_NETWORK)
DOCKER_START_NODE = 'docker run --net {cluster_network} --ip="{node_ip}" -v $(pwd)/{node_dir}:/opt/couchdb/data ' \
                    '-it dev-docker.points.com:80/couchdb2:2.0.0'
NODE_URL = 'http://{ip}:5984/{db}'
COUCHDB_CLUSTER_SETUP = {
    'url': 'http://{user}:{password}@{ip}:5984/_cluster_setup',
    'payload': '{"action":"enable_cluster", "bind_address":"0.0.0.0", "password":{password}, "port":5984, "username":{user} }',
    'finish_payload': '{"action":"finish_cluster"}'
}


def start(num_nodes, user, password):
    result = subprocess.check_output(DOCKER_CREATE_NETWORK, shell=True)
    node_ips = []
    for node in range(0, num_nodes):
        node_ip = '172.18.0.{}'.format(node)
        subprocess.check_output(DOCKER_START_NODE.format(cluster_network=DOCKER_NETWORK,
                                                         node_ip=node_ip,
                                                         node_dir='node{}'.format(node)))
        node_ips.append(node_ip)

        requests.put(url=NODE_URL.format(ip=node_ip, db='_users'))
        requests.put(url=NODE_URL.format(ip=node_ip, db='_replicator'))
        requests.put(url=NODE_URL.format(ip=node_ip, db='_global_changes'))

    master_node_ip = node_ips[0]
    response = requests.post(
        url=COUCHDB_CLUSTER_SETUP['url'].format(user=user, password=password, ip=master_node_ip),
        json=json.dumps(COUCHDB_CLUSTER_SETUP['payload'].format(user=user, password=password)))

    if response.status_code != httplib.OK:
        raise RuntimeError('Unable to setup cluster.')

    for ip in node_ips[1:]:
        requests.put(url='http://{master_node_ip}:5986/_nodes/node@{node_ip}'.format(master_node_ip=master_node_ip,
                                                                                     node_ip=ip))

    response = requests.post(
        url=COUCHDB_CLUSTER_SETUP['url'].format(user=user, password=password, ip=master_node_ip),
        json=json.dumps(COUCHDB_CLUSTER_SETUP['finish_payload'].format(user=user, password=password)))

