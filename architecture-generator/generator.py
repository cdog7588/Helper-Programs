import json
import os
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("templates"))

def render(template_name, context):
    template = env.get_template(template_name)
    return template.render(context)

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

def generate():
    with open("architecture.json") as f:
        arch = json.load(f)

    service = arch["service"]

    # Generate Controllers
    for controller in service["controllers"]:
        content = render("controller.j2", controller)
        write_file(f"output/controllers/{controller['name']}.java", content)

    # Generate Services
    for svc in service["services"]:
        content = render("service.j2", svc)
        write_file(f"output/services/{svc['name']}.java", content)

    # Generate Repositories
    for repo in service["repositories"]:
        content = render("repository.j2", repo)
        write_file(f"output/repositories/{repo['name']}.java", content)

    # Generate DTOs
    for dto in service["dtos"]:
        content = render("dto.j2", dto)
        write_file(f"output/dtos/{dto['name']}.java", content)

if __name__ == "__main__":
    generate()
