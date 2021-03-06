#!/usr/bin/python
# coding=utf-8
################################################################################

from __future__ import with_statement

from test import CollectorTestCase
from test import get_collector_config
from test import unittest
from mock import Mock
from mock import patch
from contextlib import nested

from diamond.collector import Collector
from diskspace import DiskSpaceCollector

################################################################################


class TestDiskSpaceCollector(CollectorTestCase):
    def setUp(self):
        config = get_collector_config('DiskSpaceCollector', {
            'interval': 10,
            'byte_unit': ['gigabyte'],
        })

        self.collector = DiskSpaceCollector(config, None)

    @patch('os.access', Mock(return_value=True))
    def test_get_file_systems(self):
        result = None

        with nested(
            patch('os.stat'),
            patch('os.major'),
            patch('os.minor'),
            patch('__builtin__.open', Mock(
                return_value=self.getFixture('proc_mounts')))
        ) as (os_stat_mock, os_major_mock, os_minor_mock, open_mock):
            os_stat_mock.return_value.st_dev = 42
            os_major_mock.return_value = 9
            os_minor_mock.return_value = 0

            result = self.collector.get_file_systems()

            os_stat_mock.assert_called_once_with('/')
            os_major_mock.assert_called_once_with(42)
            os_minor_mock.assert_called_once_with(42)

            self.assertEqual(result, {
                (9, 0): {
                    'device':
                    '/dev/disk/by-uuid/81969733-a724-4651-9cf5-64970f86daba',
                    'fs_type': 'ext3',
                    'mount_point': '/'}
            })

            open_mock.assert_called_once_with('/proc/mounts')
        return result

    @patch('os.access', Mock(return_value=True))
    @patch.object(Collector, 'publish')
    def test_should_work_with_real_data(self, publish_mock):
        statvfs_mock = Mock()
        statvfs_mock.f_bsize = 4096
        statvfs_mock.f_frsize = 4096
        statvfs_mock.f_blocks = 360540255
        statvfs_mock.f_bfree = 285953527
        statvfs_mock.f_bavail = 267639130
        statvfs_mock.f_files = 91578368
        statvfs_mock.f_ffree = 91229495
        statvfs_mock.f_favail = 91229495
        statvfs_mock.f_flag = 4096
        statvfs_mock.f_namemax = 255

        with nested(
            patch('os.stat'),
            patch('os.major', Mock(return_value=9)),
            patch('os.minor', Mock(return_value=0)),
            patch('os.path.isdir', Mock(return_value=False)),
            patch('__builtin__.open', Mock(
                return_value=self.getFixture('proc_mounts'))),
            patch('os.statvfs', Mock(return_value=statvfs_mock))
        ):
            self.collector.collect()

        metrics = {
            'root.gigabyte_used': (284.525, 2),
            'root.gigabyte_free': (1090.826, 2),
            'root.gigabyte_avail': (1020.962, 2),
            'root.inodes_used': 348873,
            'root.inodes_free': 91229495,
            'root.inodes_avail': 91229495
        }

        self.setDocExample(collector=self.collector.__class__.__name__,
                           metrics=metrics,
                           defaultpath=self.collector.config['path'])
        self.assertPublishedMany(publish_mock, metrics)

################################################################################
if __name__ == "__main__":
    unittest.main()
