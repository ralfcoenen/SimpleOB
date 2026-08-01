# ADR-0002: Immutable by Default

## Status

Accepted

## Kontext

Domänenobjekte sollen möglichst keine versteckten Zustandsänderungen zulassen.

## Entscheidung

Domänenobjekte werden standardmäßig als unveränderliche Dataclasses implementiert.

```python
@dataclass(frozen=True)
```

Nur wenn eine fachliche Notwendigkeit besteht, werden veränderliche Objekte eingeführt.

## Konsequenzen

* Thread-sicheres Verhalten
* Weniger Seiteneffekte
* Einfachere Tests
