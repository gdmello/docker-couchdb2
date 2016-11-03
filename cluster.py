import httplib
import json
import os
import subprocess

import requests
from retrying import retry

DOCKER_NETWORK = 'couchdb2_cluster_network'
DOCKER_CREATE_NETWORK = 'docker network create --subnet=173.19.0.0/16 {}'.format(DOCKER_NETWORK)
DOCKER_START_NODE = 'docker run --net {cluster_network} --ip="{node_ip}" -v {node_dir}:/opt/couchdb/data -d ' \
                    '--name="{node_name}" dev-docker.points.com:80/couchdb2:2.0.0'
DOCKER_FIND_NODE = 'docker ps --filter "name={node_name}" -qa'
NODE_URL = 'http://{ip}:5984/{db}'
COUCHDB_CLUSTER_SETUP = {
    'url': 'http://{ip}:5984/_cluster_setup',
    'payload': '',
    'finish_payload': '{"action":"finish_cluster"}'
}


def start(num_nodes, user, password):
    try:
        result = subprocess.check_output(DOCKER_CREATE_NETWORK, shell=True)
    except subprocess.CalledProcessError:
        print "network exists - ignoring."

    node_ips = []
    for node in range(2, int(num_nodes) + 2):
        node_ip = '173.19.0.{}'.format(node)
        node_dir = 'node{}'.format(node)
        node_dir_path = os.path.abspath(os.path.join(os.curdir, node_dir))
        if not os.path.exists(node_dir_path):
            os.makedirs(node_dir_path)
        print DOCKER_START_NODE.format(cluster_network=DOCKER_NETWORK,
                                       node_ip=node_ip,
                                       node_dir=node_dir_path,
                                       node_name='coucdhb' + node_dir)
        try:
            container_id = subprocess.check_output(DOCKER_FIND_NODE.format(node_name='coucdhb' + node_dir), shell=True)
            if container_id:
                print "removing container {}".format(container_id)
                subprocess.check_output('docker rm -f {}'.format(container_id), shell=True)
        except:
            pass
        subprocess.check_output(DOCKER_START_NODE.format(cluster_network=DOCKER_NETWORK,
                                                         node_ip=node_ip,
                                                         node_dir=node_dir_path,
                                                         node_name='coucdhb' + node_dir), shell=True)
        node_ips.append(node_ip)
        print "Initializing node"
        initial_configuration(node_ip, user, password)

    master_node_ip = node_ips[0]
    print "Enabling cluster"

    response = requests.post(
        url=COUCHDB_CLUSTER_SETUP['url'].format(ip=master_node_ip),
        json={"action": "enable_cluster",
              "bind_address": "0.0.0.0",
              "port": 5984,
              "username": "",
              "password": ""
              }
    )

    if response.status_code != httplib.CREATED:
        raise RuntimeError('Unable to setup cluster. {}'.format(response.text))

    for ip in node_ips[1:]:
        requests.put(url='http://{master_node_ip}:5986/_nodes/node@{node_ip}'.format(master_node_ip=master_node_ip,
                                                                                     node_ip=ip))

    response = requests.post(
        url=COUCHDB_CLUSTER_SETUP['url'].format(user=user, password=password, ip=master_node_ip),
        json=json.dumps(COUCHDB_CLUSTER_SETUP['finish_payload'].format(user=user, password=password)))


@retry(stop_max_attempt_number=20, wait_fixed=2000)
def initial_configuration(node_ip, user, password):
    requests.put(url=NODE_URL.format(ip=node_ip, db='_users'))
    requests.put(url=NODE_URL.format(ip=node_ip, db='_replicator'))
    requests.put(url=NODE_URL.format(ip=node_ip, db='_global_changes'))
    # requests.put(url=NODE_URL.format(ip=node_ip, db='_config'))
    # requests.put(url='http://{ip}:5986/{db}'.format(ip=node_ip, db='_config/admins/{user}'.format(user=user)), data=password)
