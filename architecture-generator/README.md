# Architecture Generator

A Python-based code generation pipeline that reads an architecture blueprint and generates Java source files for controllers, services, repositories, and DTOs.

## Structure

- architecture.json
- generator.py
- templates/
  - controller.j2
  - service.j2
  - repository.j2
  - dto.j2

## Dependency

Install Jinja2:

```bash
pip install jinja2
```

## Run

```bash
python generator.py
```

## Output

Generated files are written to:

- output/controllers/
- output/services/
- output/repositories/
- output/dtos/
