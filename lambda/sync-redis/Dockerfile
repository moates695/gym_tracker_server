FROM public.ecr.aws/lambda/python:3.11

COPY sync-redis/requirements.txt .
RUN pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

COPY shared/ ${LAMBDA_TASK_ROOT}/shared/
COPY sync-redis/app.py ${LAMBDA_TASK_ROOT}/

CMD ["app.handler"]
