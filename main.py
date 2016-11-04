import argparse
import cluster


def create_parser():
    parser = argparse.ArgumentParser(description='Setup a couchdb2 cluster')
    parser.add_argument('-n', '--num_nodes', help='Number of nodes to spin up.', default=2)
    parser.add_argument('-u', '--user', help='node admin user.', required=True)
    parser.add_argument('-p', '--password', help='node admin password.', required=True)
    return parser


if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()
    cluster.start(args.num_nodes, args.user, args.password)