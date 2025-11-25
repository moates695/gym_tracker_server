import subprocess
import shlex
import json

def main():
    bucket_name = cfn_output("GymJunkieS3Stack", "BucketName")

    subprocess.run(
        shlex.split(f"aws s3 cp ../app/envs s3://{bucket_name}/env-files --recursive"),
        check=True,
    )

    subprocess.run(
        shlex.split("./build_ecr_images.sh"),
        check=True,
    )

    ecr_stack_2_image = {
        "GymJunkieEcrApiStack": "gym-junkie-api",
        "GymJunkieEcrRedisStack": "redis",
        "GymJunkieEcrSyncRedisStack": "gym-junkie-sync-redis"
    }
    ecr_uris = {}
    for ecr_stack in ecr_stack_2_image.keys():
        ecr_uris[ecr_stack] = cfn_output(ecr_stack, "RepoUri")

    for ecr_stack, image in ecr_stack_2_image.items():
        subprocess.run(
            shlex.split(f"""
                docker tag {image}:latest {ecr_uris[ecr_stack]}:latest
            """),
            check=True
        )
        subprocess.run(
            shlex.split(f"""
                docker push {ecr_uris[ecr_stack]}:latest
            """),
            check=True
        )    

def cfn_output(stack, output_key):
    command = f"""
        aws cloudformation describe-stacks
            --stack-name {stack}
            --query 'Stacks[0].Outputs'
            --output json
    """

    result_json = json.loads(subprocess.run(
        shlex.split(command),
        check=True,
        capture_output=True,
        text=True
    ).stdout)

    for result in result_json:
        if result.get("OutputKey") != output_key: continue
        return result.get("OutputValue")
    else:
        raise Exception(f"output key '{output_key}' not found from stack '{stack}'")

if __name__ == "__main__":
    main()