#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import boto3
import logging
import os
import ipaddress
from sensu_plugin import SensuPluginCheck

try:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
except Exception:
    logger.error("An error has occured. Cannot set logger!")

class SubnetCheck(SensuPluginCheck):
    def setup(self):
        # Setup is called with self.parser set and is responsible for setting up
        # self.options before the run method is called

        self.parser.add_argument(
            '-w',
            '--warning',
            default=20,
            type=int,
            help='warning threshold for percentage of subnet available IPs, default to 20'
        )
        self.parser.add_argument(
            '-c',
            '--critical',
            default=10,
            type=int,
            help='critical threshold for percentage of subnet available IPs, default to 10'
        )
        self.parser.add_argument(
            '-r',
            '--region',
            default='us-west-2',
            type=str,
            help='specify aws region. default to us-west-2'
        )
        self.parser.add_argument(
            '-vpcid',
            '--vpcid',
            default=None,
            type=str,
            help='specify comma separated list of vpc ids. For example: vpc-abc123,vpc-xyz123'
        )

    def run(self):
        # this method is called to perform the actual check
        self.check_subnet() # defaults to class name

        if self.options.warning == 0:
            self.ok(self.options.message)
        elif self.options.warning == 1:
            self.warning(self.options.message)
        elif self.options.warning == 2:
            self.critical(self.options.message)
        else:
            self.unknown(self.options.message)

    def check_subnet(self):
        """
        check subnet
        """
        region = self.options.region
        ec2 = boto3.resource('ec2', region)
        client = boto3.client('ec2', region)
        threshold_warning = self.options.warning
        threshold_critical = self.options.critical

        # check if specific vpc ids are given
        if not self.options.vpcid:
            selected_vpcids = [x.strip()
                               for x in self.options.vpcid.split(',')]

        if threshold_warning >= 100 or threshold_warning <= 0:
            logger.warning(
                "-w indicates warning percentage of available IPs. It must be < 100 and > 0. Set to default value of 10")
            threshold_warning = 20

        if threshold_critical >= 100 or threshold_critical <= 0:
            logger.warning(
                "-c indicates critical percentage of available IPs. It must be < 100 and > 0. Set to default value of 10")
            threshold_critical = 10

        filters = []
        subnets = list(ec2.subnets.filter(Filters=filters))
        data = {}

        self.options.warning = 0 # OK
        for subnet in subnets:
            subnet_info = ec2.Subnet(subnet.id)
            total_available_ips = ipaddress.ip_network(subnet_info.cidr_block).num_addresses - 5
            if subnet_info.available_ip_address_count / total_available_ips * 100 <= threshold_critical:
                self.options.warning = 2 # CRITICAL
            elif subnet_info.available_ip_address_count / total_available_ips * 100 <= threshold_warning:
                self.options.warning = 1 # WARNING

            if self.options.warning in [1, 2]:
                if not selected_vpcids and subnet_info.vpc_id not in selected_vpcids:
                    continue

                if subnet_info.vpc_id not in data:
                    data[subnet_info.vpc_id] = []

                data[subnet_info.vpc_id].append(
                    (subnet.id, subnet_info.available_ip_address_count, total_available_ips))

        msg = []
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

            msg.append("The following subnets are running out of ipv4 capacity:\n{}/{} ({})".format(region, vpc_id, vpc_name))
            for row in data[vpc_id]:
                msg.append("\t- {} has {} available IPs out of {}".format(row[0], row[1], row[2]))

        self.options.message = "\n".join(msg)

if __name__ == "__main__":
    f = SubnetCheck()

