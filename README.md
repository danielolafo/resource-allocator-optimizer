# AI Resource Allocator (Python)

Optimizador en Python que recibe una lista de empleados con sus tecnologías
(nombre, versión, nivel de dominio, años de experiencia) y su asignación actual
(a qué proyecto y cuándo termina), y distribuye a cada empleado en los proyectos
donde aplica. Busca **maximizar** la cantidad de empleados ocupados, el tiempo
de asignación (0 % tiempo ocioso cuando hay proyectos disponibles) y **las
ganancias monetarias**.

Los modelos de entrada (`allocator/models.py`) reflejan las interfaces de
TypeScript del frontend Angular (`Assignment`, `EmployeeTechnology`,
`Employee`, `Project`, `Technology`).

## Objetivos optimizados

1. **Ocupación** — ningún empleado sin asignar cuando exista un proyecto donde
   aplique.
2. **Tiempo** — se rellenan las ventanas libres de cada empleado entre su
   asignación actual y el final del horizonte.
3. **Ganancia** — se priorizan las parejas (empleado, proyecto) con mayor
   margen diario `project.dailyRate - employee.costPerDay`.

Dos campos monetarios opcionales se añaden a los modelos (`Employee.costPerDay`
y `Project.dailyRate`); si no se envían, se usan los valores por defecto.

## Algoritmo ("IA" heurística)

```
1. Filtrado de factibilidad   -> tecnología + versión compatible (mismo major
                                 y versión >= requerida) + nivel + años de exp.
2. Greedy por beneficio       -> se reserva primero la pareja más rentable
                                 dentro de su ventana válida.
3. Relleno de huecos          -> empleados con días libres se asignan a
                                 proyectos que aún necesiten ese skill.
4. Búsqueda local             -> intercambios acotados que suben el beneficio
                                 global sin romper restricciones.
```

Invariantes garantizados: sin doble reserva por día, sin sobrepasar la
capacidad de cada slot de proyecto y respetando versión/nivel/experiencia.

## Instalación

```bash
cd ai-allocator
pip install -r requirements.txt
```

Solo hace falta `pydantic` para la lógica; `fastapi`/`uvicorn` son opcionales
para exponer la API.

## Uso CLI

```bash
python cli.py generate samples/sample.json
python cli.py assign samples/sample.json --output samples/result.json
python cli.py assign samples/sample.json --today 2026-09-16
```

Formato del JSON de entrada (mismas claves que las interfaces TS):

```json
{
  "technologies": [{ "id": 1, "name": "Angular", "version": "18.2", ... }],
  "employees": [{
     "id": 1,
     "firstName": "Ana",
     "lastName": "García",
     "email": "...",
     "position": "Senior Frontend",
     "hireDate": "2020-03-01",
     "costPerDay": 350,
     "technologies": [
       { "technologyId": 2, "level": "EXPERT", "version": "18.2", "yearsExperience": 5 }
     ]
  }],
  "projects": [{
     "id": 1,
     "name": "Portal Bancario",
     "client": "Banco Central",
     "status": "ACTIVE",
     "startDate": "2026-01-01",
     "endDate": "2026-12-31",
     "dailyRate": 1800,
     "requiredTechnologies": [
       { "technologyId": 2, "version": "18.2", "minLevel": "ADVANCED",
         "minYearsExperience": 2, "count": 2 }
     ]
  }],
  "assignments": [
     { "id": 1, "employeeId": 1, "projectId": 1, "startDate": "2026-01-01",
       "endDate": "2026-03-01" }
  ]
}
```

La salida incluye `assignments` (asignaciones nuevas + las actuales que siguen
vigentes), `summary` (empleados ocupados/ociosos, días asignados, utilización por
empleado y beneficio total) y `warnings`.

## API (integración con Angular)

```bash
uvicorn api.main:app --reload --port 8000
```

- `GET  /health`
- `POST /allocate` — recibe el mismo JSON y devuelve `assignments`+`summary`.

La app Angular puede hacer `POST http://localhost:8000/allocate` con su
`employees`/`projects`/`assignments` actuales y mostrar la planificación.

## Tests

```bash
python -m unittest discover -s tests -v
```