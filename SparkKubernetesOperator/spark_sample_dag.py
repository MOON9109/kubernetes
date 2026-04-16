from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import SparkKubernetesOperator
from airflow.providers.cncf.kubernetes.sensors.spark_kubernetes import SparkKubernetesSensor
from datetime import datetime

with DAG(
    dag_id='execute_spark_on_k8s',
    start_date=datetime(2026, 1, 1),
    catchup=False,
    schedule=None
) as dag:
    Appication_name='spark-pi-{{ ds_nodash }}'
    # 1. SparkApplication 리소스 생성 (Job 제출)
    submit_spark = SparkKubernetesOperator(
        task_id='submit_spark',
        namespace="spark-jobs",  # 아까 만든 spark 전용 네임스페이스
        # 아래 정의할 YAML 내용을 직접 넣거나 파일 경로를 적습니다.
        delete_on_termination=False,
        #Application py,jar 파일은 별도의 공유 볼륨(PVC)을 만들고, GitSync가 최신 코드를 그 볼륨에 계속 업데이트하거나 s3에 업로드
        application_file=f"""
apiVersion: "sparkoperator.k8s.io/v1beta2"
kind: SparkApplication
metadata:
  name: {Appication_name}
  namespace: spark-jobs
spec:
  type: Python
  mode: cluster
  image: "apache/spark-py:v3.4.0"
  mainApplicationFile: "local:///opt/spark/examples/src/main/python/pi.py" 
  arguments:
    - "10"  
  sparkVersion: "3.4.0"
  driver:
    cores: 1
    memory: "512m"
    serviceAccount: spark-operator-spark
  executor:
    cores: 1
    instances: 1
    memory: "512m"
  timeToLiveSeconds: 300
  template:
    cleanupPolicy:
        strategy: Never
""",
        kubernetes_conn_id="kubernetes_default",
    )

    # 2. 작업이 끝날 때까지 대기 및 상태 모니터링
    monitor_spark = SparkKubernetesSensor(
        task_id='monitor_spark',
        namespace="spark-jobs",
        application_name="{{ task_instance.xcom_pull(task_ids='submit_spark', key='pod_name').replace('-driver', '') }}",
        kubernetes_conn_id="kubernetes_default",
    )

    submit_spark >> monitor_spark

