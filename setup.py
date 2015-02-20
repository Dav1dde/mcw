#!/usr/bin/env python2
# -*- coding: utf8 -*-

from setuptools import setup, find_packages


if __name__ == '__main__':
    setup(
        name='mcw',
        version='0.1.0a0',
        packages=find_packages(),
        include_package_data=True,
        zip_safe=False,
        install_requires=[
            'gevent',
            'flask',
            'flask-socketio',
            'blinker'
        ],
        entry_points={
            'console_scripts': [
                'mcw = mcw.__main__:main'
            ]
        }
    )
