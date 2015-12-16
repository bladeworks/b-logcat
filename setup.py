from setuptools import setup

setup(
        name='blade-logcat',
        version='1.0',
        py_modules=['logcat'],
        include_package_data=True,
        install_requires=[
            'click',
            'colorama',
            'subprocess32',
            ],
        entry_points='''
        [console_scripts]
        logcat=logcat:cli
        ''',
)
