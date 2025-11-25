import subprocess
import shlex
import json

from deploy import cfn_output

def main():
    db_sg_id = cfn_output("GymJunkieSecurityGroupStack", "DbSgId")

    subprocess.run(
        shlex.split(f"""
            aws rds modify-db-instance
                --db-instance-identifier gym-junkie-postgres
                --vpc-security-group-ids {db_sg_id} \
                --apply-immediately
        """),
        check=True,
    )

if __name__ == "__main__":
    main()