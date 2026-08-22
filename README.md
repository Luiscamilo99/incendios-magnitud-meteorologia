# Configuración de la API CDS

Las credenciales de Copernicus Climate Data Store no deben escribirse en el notebook ni subirse a GitHub.

En Windows PowerShell, configura la clave solo en tu equipo:

```powershell
$env:CDSAPI_KEY = "TU_ID:TU_API_KEY"
```

Para dejarla disponible en futuras sesiones de PowerShell, usa `setx CDSAPI_KEY "TU_ID:TU_API_KEY"` y abre una nueva terminal. No compartas ese valor.

También puedes crear el archivo `%USERPROFILE%\.cdsapirc` fuera del repositorio con:

```yaml
url: https://cds.climate.copernicus.eu/api
key: TU_ID:TU_API_KEY
```

El notebook comprueba `CDSAPI_KEY` primero y, si no existe, `cdsapi` puede usar `.cdsapirc`.
# incendios-magnitud-meteorologia
