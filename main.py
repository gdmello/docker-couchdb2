import argparse
import cluster


def create_parser():
    parser = argparse.ArgumentParser(description='Setup a couchdb2 cluster')
    parser.add_argument('-n', '--num_nodes', help='Number of nodes to spin up.', default=2)
    parser.add_argument('-a', '--user', help='node admin user.', required=True)
    parser.add_argument('-p', '--password', help='node admin password.', required=True)

    parser.add_argument('-si', '--source_index', help='Source Elasticsearch index.', default='lcp_v2')
    parser.add_argument('-du', '--destination_user', help='Destination Elasticsearch admin username.', required=True)
    parser.add_argument('-dp', '--destination_password', help='Destination Elasticsearch admin password.',
                        required=True)
    parser.add_argument('-di', '--destination_index', help='Destination Elasticsearch index.', default='lcp_v2_copy')
    parser.add_argument('-d', '--destination',
                        help='Destination Elasticsearch host in which the new sanitized index will be created.',
                        required=True)
    parser.add_argument('-rd', '--reset_destination',
                        help='Reset the Destination Elasticsearch index. If it exists it will be deleted first.',
                        default=False, action="store_true")
    parser.add_argument('-n', '--max_threads', help='Maximum number of threads of execution.', default=2)
    return parser


if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()
    cluster.start()