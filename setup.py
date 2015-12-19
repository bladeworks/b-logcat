from setuptools import setup

setup(
        name='b-logcat',
        version='1.0.1',
        author='Blade Liu',
        author_email='flyblade@gmail.com',
        url='https://github.com/bladeworks/b-logcat',
        description='A small tool to view / filter the android logs.',
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
