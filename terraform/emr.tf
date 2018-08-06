resource "aws_emr_cluster" "emr-spark-cluster" {
  name          = "GeoPySpark Cluster"
  applications  = ["Hadoop", "Spark", "Ganglia"]
  log_uri       = "${var.s3_log_uri}"
  # Don't use emr version >5.12.1; Spark 2.3 currently incompatible w/ rasterframes
  release_label = "emr-5.12.1"
  service_role  = "${var.emr_service_role}"

  step {
    name="Sync CVML"
    action_on_failure = "CONTINUE"
    hadoop_jar_step {
    jar="command-runner.jar"
    args = ["aws","s3","sync","s3://activemapper/cvmlAL/","/home/hadoop/cvmlAL"]
  }} 

  step {
    name="Run CVML"
    action_on_failure = "CONTINUE"
    hadoop_jar_step {
    jar="command-runner.jar"
    args = ["python3","/home/hadoop/cvmlAL/run_it/cvml_mapper_connection.py"]
  }} 

  ec2_attributes {
    subnet_id        = "${var.subnet}"
    instance_profile = "${var.emr_instance_profile}"
    key_name         = "${var.key_name}"

    emr_managed_master_security_group = "${var.user_defined_sg == "true" ? var.security_group : aws_security_group.security-group.id}"
    emr_managed_slave_security_group  = "${var.user_defined_sg == "true" ? var.security_group : aws_security_group.security-group.id}"
  }

  instance_group {
    # bid_price      = "${var.bid_price}"
    instance_count = 1
    instance_role  = "MASTER"
    instance_type  = "m3.xlarge"
    name           = "geopyspark-master"
  }

  instance_group {
    bid_price      = "${var.bid_price}"
    instance_count = "${var.worker_count}"
    instance_role  = "CORE"
    instance_type  = "m3.xlarge"
    name           = "geopyspark-core"
  }

  bootstrap_action {
    path = "s3://${var.bs_bucket}/${var.bs_prefix}/bootstrap.sh"
    name = "geopyspark"
    args = [
      "${var.s3_rpm_uri}",
      "${var.s3_notebook_uri}",
      "${var.geopyspark_jars}",
      "${var.geopyspark_uri}",
      "${var.rasterframes_sha}",
      "${var.rasterframes_version}"
    ]
  }

  configurations = "cluster-configurations.json"

  depends_on = ["aws_s3_bucket_object.bootstrap"]
}

output "emr-id" {
  value = "${aws_emr_cluster.emr-spark-cluster.id}"
}

output "emr-master" {
  value = "${aws_emr_cluster.emr-spark-cluster.master_public_dns}"
}
