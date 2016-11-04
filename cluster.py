import httplib
import os
import subprocess

import requests
from retrying import retry

DOCKER_NETWORK = 'couchdb2_cluster_network'
DOCKER_CREATE_NETWORK = 'docker network create --subnet=173.19.0.0/16 {}'.format(DOCKER_NETWORK)
DOCKER_START_NODE = 'docker run --net {cluster_network} --ip="{node_ip}" -v {node_dir}:/opt/couchdb/data -d ' \
                    '-v {node_etc_dir}:/opt/couchdb/etc --name="{node_name}" dev-docker.points.com:80/couchdb2:2.0.0'
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
        print ("network exists - ignoring.")

    node_ips = []
    for node_num in range(2, int(num_nodes) + 2):
        node_ip = '173.19.0.{}'.format(node_num)
        node_dir = 'node{}'.format(node_num)

        try:
            container_name = 'couchdb' + node_dir
            container_id = subprocess.check_output(DOCKER_FIND_NODE.format(node_name=container_name), shell=True)
            if container_id:
                print ("removing container {}".format(container_id))
                subprocess.check_output('docker rm -f {}'.format(container_id), shell=True)
        except:
            pass

        node_dir_path, node_config_path = make_node_config(node_dir, node_ip, node_num)
        start_cmd = DOCKER_START_NODE.format(cluster_network=DOCKER_NETWORK,
                                             node_ip=node_ip,
                                             node_dir=node_dir_path,
                                             node_etc_dir=node_config_path,
                                             node_name=container_name)
        print start_cmd
        subprocess.check_output(start_cmd, shell=True)
        node_ips.append(node_ip)
        print ("Initializing node")
        initial_configuration(node_num, node_ip, user, password)

    master_node_ip = node_ips[0]
    print ("Enabling cluster")

    enable_cluster(master_node_ip)

    for ip in node_ips[1:]:
        url = 'http://{master_node_ip}:5984/_cluster_setup'.format(master_node_ip=master_node_ip)
        print ("Adding node {} to cluster {}".format(ip, url))
        response = requests.post(url=url, json={"action": "enable_cluster",
                                                "host": ip,
                                                "bind_address": "0.0.0.0",
                                                "port": 5984
                                                })
        print (response.text)

    response = requests.post(
        url=COUCHDB_CLUSTER_SETUP['url'].format(user=user, password=password, ip=master_node_ip),
        json={"action": "finish_cluster"})


def make_node_config(node_dir, node_ip, node_num):
    import shutil
    config_path = os.path.abspath(os.path.join(os.curdir, 'config'))
    node_dir_path = os.path.abspath(os.path.join(os.curdir, node_dir))
    if os.path.exists(node_dir_path):
        cmd = 'docker run -v {}:/node_dir --entrypoint="/bin/sh" --rm alpine -c "rm -rf /node_dir/{}" '.format(
            os.path.abspath(os.curdir), node_dir)
        print cmd
        subprocess.check_output(cmd, shell=True)

    node_config_path = os.path.abspath(os.path.join(node_dir_path, 'config'))
    shutil.copytree(config_path, node_config_path)
    with open(os.path.join(node_config_path, 'vm.args'), 'r+') as f:
        vm_config = f.read()
        vm_config = vm_config.replace('{{node_name}}', '-name couchdbnode{}@{}'.format(node_num, node_ip))
        f.seek(0)
        f.write(vm_config)
        f.truncate()

    return node_dir_path, node_config_path


def enable_cluster(master_node_ip):
    response = requests.post(
        url=COUCHDB_CLUSTER_SETUP['url'].format(ip=master_node_ip),
        json={"action": "enable_cluster",
              "bind_address": "0.0.0.0",
              "port": 5984
              }
    )
    if response.status_code != httplib.CREATED:
        raise RuntimeError('Unable to setup cluster. {}'.format(response.text))


@retry(stop_max_attempt_number=20, wait_fixed=2000)
def initial_configuration(node_num, node_ip, user, password):
    requests.put(url=NODE_URL.format(ip=node_ip, db='_users'))
    requests.put(url=NODE_URL.format(ip=node_ip, db='_replicator'))
    requests.put(url=NODE_URL.format(ip=node_ip, db='_global_changes'))
    requests.put(url=NODE_URL.format(ip=node_ip, db='_metadata'))
    # Setup admin user
    response = requests.put(
        url=NODE_URL.format(ip=node_ip, db='_node/couchdbnode{}@{}/_config/admins/{}'.format(node_num, node_ip, user)),
        json=password)
    # import ipdb
    # ipdb.set_trace()
    # Bind to external/ docker container address
    response = requests.put(
        url=NODE_URL.format(ip=node_ip, db='_node/couchdb@{}/_config/chttpd/bind_address'.format(node_ip)),
        json='0.0.0.0')
    # requests.put(url='http://{ip}:5986/{db}'.format(ip=node_ip, db='_config/admins/{user}'.format(user=user)), data=password)
