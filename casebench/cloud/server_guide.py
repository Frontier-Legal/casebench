"""Where a team server comes from: what to run on the machine lawyers reach (decision 0064)."""

GUIDE = "https://github.com/Frontier-Legal/casebench/blob/main/ee/README.md"
EXAMPLE = "https://casebench.firm.example"


def set_up() -> list[str]:
    """The steps, in order, for a person or a coding agent to follow on the server, then on
    this machine. Nothing here installs or runs them."""
    return [
        "On a machine lawyers can reach, such as a company server, install the team server:",
        "  pip install casebench-ee",
        "  CASEBENCH_DATABASE_URL=postgresql://USER:PASSWORD@HOST/casebench \\",
        f"  CASEBENCH_PUBLIC_URL={EXAMPLE} casebench-team serve --host 0.0.0.0",
        f"  or run its container image, as {GUIDE} says",
        "Its first start prints a one-time setup code: open the address, enter the code and "
        "create the first admin.",
        "On the Team page, the admin makes an API key with the engineer role; set it here as "
        "CASEBENCH_CLOUD_KEY, in the environment or a .env file.",
        f"Then, here: casebench init --team-server {EXAMPLE}",
    ]
