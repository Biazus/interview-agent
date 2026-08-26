from dataclasses import dataclass


@dataclass(frozen=True)
class DomainRagConfig:
    collection_name: str
    seed_manifest_files: tuple[str, ...]
    seed_yaml_path: str
