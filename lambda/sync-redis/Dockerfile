FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt ${LAMBDA_TASK_ROOT}

RUN pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

COPY lambda_function.py ${LAMBDA_TASK_ROOT}

ADD https://s3.amazonaws.com/aws-lambda-extensions-preview-us-east-1/ps-exec-extension/ps-exec-extension.zip /opt/extensions/

CMD [ "lambda_function.handler" ]