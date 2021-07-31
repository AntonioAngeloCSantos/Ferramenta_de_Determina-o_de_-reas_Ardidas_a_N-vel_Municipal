from setuptools import setup

setup(
    name='sentinel',
    version='0.1',
    author = "Antonio Angelo Candeias dos Santos",
    description="""Ferramenta para determinação de Áreas Ardidas a Nível Municipal com recurso imagens Sentinel2 com resolução 10 metros""",
    license='MIT',
    packages=['sentinel'],
    zip_safe=False,
      install_requires=[
   'sentinelsat==0.14'
]

)
