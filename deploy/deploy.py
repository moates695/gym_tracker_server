import subprocess
import shlex
import json

def main():
    subprocess.run(
        shlex.split("./build_ecr_images.sh"),
        check=True,
    )

    ecr_stack_2_image = {
        "EcrApiStack": "gym-junkie-api",
        "EcrRedisStack": "redis",
        "EcrSyncRedisStack": "gym-junkie-sync-redis"
    }
    ecr_uris = {}
    for ecr_stack in ecr_stack_2_image.keys():
        command = f"""
            aws cloudformation describe-stacks
                --stack-name {ecr_stack}
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
            if result.get("OutputKey") != "RepoUri": continue
            ecr_uris[ecr_stack] = result["OutputValue"]
            break
        else:
            raise Exception(f"no repo uri found for {ecr_stack}")

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

if __name__ == "__main__":
    main()