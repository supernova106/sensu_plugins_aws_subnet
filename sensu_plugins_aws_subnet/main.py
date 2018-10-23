#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import boto3
import logging
import os
import ipaddress
from sensu_plugin import SensuPluginCheck

my_session = boto3.session.Session()
region = my_session.region_name
ec2 = boto3.resource('ec2', region)
client = boto3.client('ec2', region)

try:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
except Exception:
    logger.error("An error has occured. Cannot set logger!")

def check_subnet():
    """
    check subnet
    """
    try:
        threshold = int(os.environ['SUBNET_THRESHOLD'])

        if threshold >= 100 or threshold <= 0:
            logger.warning(
            "SUBNET_THRESHOLD indicates percentage of available IPs. It must be < 100 and > 0. Set to default value of 20")
            threshold = 20
    except KeyError:
        logger.warning('SUBNET_THRESHOLD is not set. Set to default value of 20')
        threshold = 20

    filters = []
    subnets = list(ec2.subnets.filter(Filters=filters))
    data = {}
    for subnet in subnets:
        subnet_info = ec2.Subnet(subnet.id)
        total_available_ips = ipaddress.ip_network(subnet_info.cidr_block).num_addresses - 5
        if subnet_info.available_ip_address_count/total_available_ips*100 <= threshold:
            if subnet_info.vpc_id not in data:
                data[subnet_info.vpc_id] = []

            data[subnet_info.vpc_id].append(
                (subnet.id, subnet_info.available_ip_address_count, total_available_ips))

    for vpc_id in data:
        vpc_info = client.describe_vpcs(
            VpcIds=[
                vpc_id,
            ]
        )

        vpc_name = ""
        for value in vpc_info['Vpcs']:
            if 'Tags' in value:
                for tag in value['Tags']:
                    if tag['Key'] == 'Name':
                        vpc_name = tag['Value']

        print("The following subnets are running out of ipv4 capacity:\n{}/{} ({})".format(region,
            vpc_id, vpc_name))
        for row in data[vpc_id]:
            print("\t- {} has {} available IPs out of {}".format(row[0],row[1],row[2]))

if __name__ == "__main__":
    check_subnet()


