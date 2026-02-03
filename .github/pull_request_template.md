## Descripción

<!-- Describe los cambios que estás proponiendo -->

**Tipo de cambio:**
- [ ] Bug fix (corrección de bug)
- [ ] Nueva funcionalidad
- [ ] Cambio de comportamiento (breaking change)
- [ ] Refactorización
- [ ] Mejora de documentación
- [ ] Mejora de performance
- [ ] Cambio de seguridad

## Motivación y Contexto

<!-- ¿Por qué es necesario este cambio? ¿Qué problema resuelve? -->

Fixes #(número de issue)

## Cambios Realizados

<!-- Lista los cambios principales -->

- 
- 
- 

## Testing

<!-- Describe las pruebas que has realizado -->

- [ ] Tests unitarios pasan: `pytest tests/ -v`
- [ ] Tests de integración pasan
- [ ] He probado manualmente los cambios
- [ ] He probado edge cases

**Comandos ejecutados:**
```bash
# Ejemplo de comandos de test que ejecutaste
pytest tests/test_transcriber_engine.py -v
```

## Calidad de Código

- [ ] Código sigue PEP 8: `flake8 src/ tests/`
- [ ] Formato aplicado: `black src/ tests/`
- [ ] Imports organizados: `isort src/ tests/`
- [ ] Type hints verificados: `mypy src/`
- [ ] Seguridad verificada: `bandit -r src/`

## Screenshots (si aplica)

<!-- Si hay cambios visuales, agrega screenshots o GIFs -->

## Checklist de Revisión

- [ ] Mi código sigue las guías de estilo del proyecto
- [ ] He realizado una auto-revisión de mi código
- [ ] He comentado mi código, especialmente en áreas complejas
- [ ] He actualizado la documentación correspondiente
- [ ] Mis cambios no generan warnings nuevos
- [ ] He agregado tests que prueban mi fix o funcionalidad
- [ ] Todos los tests pasan localmente
- [ ] Los cambios son backward compatible (si aplica)

## Impacto en Seguridad

<!-- Si tu cambio afecta seguridad, descríbelo -->

- [ ] No hay impacto de seguridad
- [ ] He considerado aspectos de seguridad en mi cambio

**Descripción de seguridad (si aplica):**

## Dependencias

<!-- Lista nuevas dependencias agregadas o dependencias que se deben actualizar -->

Nuevas dependencias:
- 

Dependencias actualizadas:
- 

## Información Adicional

<!-- Cualquier otra información relevante para los revisores -->

---

**Nota para revisores:** Por favor revisa que:
1. Los tests pasan en CI
2. La documentación está actualizada
3. No hay problemas de seguridad con Bandit
4. El código es mantenible y sigue los estándares
