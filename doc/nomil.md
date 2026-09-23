# How the NOMIL API was located

The NOMIL website only publishes per-route PDF calendars. The live data lives
behind the **NoMil Tømmeplan** mobile app (developer: Norconsult Digital AS,
formerly Norconsult Informasjonssystemer AS; package
`com.norconsult.tommeplan.nomil`).

Steps:

1. The app is a **Xamarin / .NET** app. The Android APK stores its .NET
   assemblies in `assemblies/assemblies.blob` (an `XABA` store of per-assembly
   `XALZ` = LZ4-compressed payloads).
2. Decompiling `Mobil.Tommeplan.Core.dll` revealed an embedded JSON config and
   the `RemoteStorageService` class, which contains the full networking logic.

Key config (`Settings`):

```json
{
  "WebserviceUrl": "https://tommeplan.nomil.no:9000/api/",
  "Oppdragsgiver": "100",
  "ApplikasjonsId": "380b0118-95ba-4c57-b53c-2f79c3922d65",
  "MeldingOpphavId": "7"
}
```

Auth flow (`RemoteStorageService.LogInToServer`):

- `POST {base}login` with body
  `{"applikasjonsId": ApplikasjonsId, "oppdragsgiverId": Oppdragsgiver}`.
- On success the server returns a `Token` response header (a GUID).
- That token is sent as a `Token:` request header on all subsequent GETs.
  A 401 triggers a re-login and one retry.

Endpoints (all relative to `WebserviceUrl`):

| Method call | Path |
|---|---|
| `CollectionPropertyItemsAsync(searchTerm)` | `eiendommer?adresse={q}` |
| `CollectionPropertyItemsAsync(lat,lon)` | `eiendommer/hentestedGeolokasjon?breddegrad={lat}&lengdegrad={lon}` |
| `CollectionCalendarItemsAsync(eiendomId)` | `tomminger?eiendomId={id}&datoFra={from}&datoTil={to}` |
| `GetOppdragsgiver(id)` | `oppdragsgiver?oppdragsgiverId={id}` |
| recycling stations | `stasjoner` |
| deviation categories/types | `meldinger/kategorier?meldingOpphavId={id}`, `meldinger/typer?meldingKategoriId={id}` |
| video links | `videolinker` |

Dates in query params use `yyyy-MM-dd`. Response dates come back as
`yyyy-MM-ddT00:00:00`.

The same backend (`*.tommeplan.*` apps, one `oppdragsgiverId` per company)
serves many other Norwegian waste companies using the identical Norconsult
framework, so the same three-call pattern likely works for them by swapping the
host, `applikasjonsId`, and `oppdragsgiverId`.
