**************
Setup Database
**************


Local
=====

Coming soon


Cloud
=====

Amazon Web Services
-------------------

AWS provide a managed relational database service `Amazon Relational Database Service (RDS)`_ with several database instance types and a `PostgreSQL`_  database engine.



*0. Prerequisites*

\* Configure `Amazon Relational Database Service (RDS)`_  with `PostgreSQL`_  version 9.5 + with properly `Amazon RDS Security Groups`_ and subnet group for the RDS configured (see `Tutorial Create an Amazon VPC for Use with an Amazon RDS DB Instance`_)


\* Open Datacube supports NETCDF CF and S3 drivers for storage (see `Open DataCube Ingestion Config`_). Different software dependencies are required for different drivers. Choose one of the drivers supported by Open DataCube according to your application. For NETCDF CF we use `Amazon Elastic File System`_ and for S3 driver we use `Amazon S3`_ . 

.. note:: 

	If S3 driver for storage of Open DataCube is selected, you need to create a bucket on S3. `Boto3 Documentation`_ and AWS suggests as a best practice using `IAM Roles for Amazon EC2`_. See `Best Practices for Configuring Credentials`_.
	



.. _Boto3 Documentation: http://boto3.readthedocs.io/en/latest/index.html 
	
.. _PostgreSQL: https://www.postgresql.org/

.. _Amazon Relational Database Service (RDS): https://aws.amazon.com/rds/

.. _Tutorial Create an Amazon VPC for Use with an Amazon RDS DB Instance: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Tutorials.WebServerDB.CreateVPC.html

.. _Amazon RDS Security Groups: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.RDSSecurityGroups.html

.. _IAM Roles for Amazon EC2: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html
	
.. _Best Practices for Configuring Credentials: http://boto3.readthedocs.io/en/latest/guide/configuration.html#best-practices-for-configuring-credentials

.. _Amazon S3: https://aws.amazon.com/s3/

.. _Amazon Elastic File System: https://aws.amazon.com/efs/ 

.. _Open DataCube Ingestion Config: https://datacube-core.readthedocs.io/en/latest/ops/ingest.html#ingestion-config

