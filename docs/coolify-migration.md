# Coolify Migration Guide

How to move the Arxivian stack from one VPS / Coolify server to another.

## What holds state

| Volume | Service | Contents | Critical? |
|---|---|---|---|
| `postgres_data` | `db` (pgvector) | Papers, chunks, conversations, users, agent executions | **Yes** |
| `langfuse_postgres_data` | `langfuse-db` | LLM observability history | Optional |
| `redis_data` | `redis` | Celery broker queue, LangGraph checkpoints, embedding cache | No -- ephemeral |

Everything else (app, celery-worker, celery-beat, frontend, flower, langfuse) is **stateless** and rebuilt from images + env vars on deploy.

## Migration steps

### 1. Export the databases on the old server

```bash
# Main database (required)
docker exec <db_container> pg_dump -U arxiv_user -d arxiv_rag -Fc > arxiv_rag.dump

# Langfuse database (optional -- can start fresh)
docker exec <langfuse_db_container> pg_dump -U langfuse -d langfuse -Fc > langfuse.dump
```

`-Fc` produces a custom-format dump that handles pgvector extensions and supports selective `pg_restore`.

### 2. (Optional) Export Redis

Redis data in this stack is mostly ephemeral:

- DB 0: Celery broker + LangGraph checkpoints (losing this means users restart conversations)
- DB 1: Celery result backend (safe to lose)
- DB 2: Embedding cache (rebuilt automatically on next queries)

If you want it anyway:

```bash
docker exec <redis_container> redis-cli -a "$REDIS_PASSWORD" BGSAVE
docker cp <redis_container>:/data/dump.rdb ./dump.rdb
```

### 3. Transfer files to the new server

```bash
scp arxiv_rag.dump new-server:/tmp/
scp langfuse.dump new-server:/tmp/       # if migrating Langfuse
scp dump.rdb new-server:/tmp/            # if migrating Redis
```

### 4. Deploy on the new Coolify server

1. Create the project in Coolify, point it to the repo.
2. Fill in all environment variables (copy from old Coolify instance).
3. Deploy once so containers and volumes are created.
4. **Stop the stack** before restoring data.

### 5. Restore databases

```bash
# Main database
docker exec -i <new_db_container> pg_restore \
  -U arxiv_user -d arxiv_rag --clean --if-exists < /tmp/arxiv_rag.dump

# Langfuse database (if migrating)
docker exec -i <new_langfuse_db_container> pg_restore \
  -U langfuse -d langfuse --clean --if-exists < /tmp/langfuse.dump
```

For Redis: stop the Redis container, copy `dump.rdb` into the volume mount path, restart.

### 6. Start the stack and verify

```bash
# Health check
curl -f http://localhost:8000/api/v1/health

# Verify data exists (connect to DB and spot-check)
docker exec -it <new_db_container> psql -U arxiv_user -d arxiv_rag \
  -c "SELECT count(*) FROM papers;"
```

### 7. DNS cutover

- Update DNS A/CNAME records to point to the new server IP.
- Re-assign domains in Coolify UI for frontend, flower, and langfuse.
- Enable TLS in Coolify for each public service.

## Migrating Coolify itself

If you also need to move the **Coolify instance** (not just the app), see the
[official backup/restore docs](https://coolify.io/docs/knowledge-base/how-to/backup-restore-coolify).
The key steps are:

1. Dashboard > Settings > Backup > "Backup Now" and download the file.
2. Save your `APP_KEY` from `/data/coolify/source/.env`.
3. Copy SSH keys from `/data/coolify/ssh/keys/`.
4. Install fresh Coolify on the new server (same version).
5. Stop Coolify containers, `pg_restore` the backup into `coolify-db`.
6. Set `APP_PREVIOUS_KEYS=<old_key>` in the new `.env`.
7. Restart Coolify.

## Tools that can help

### Docker-native

| Tool | What it does | Link |
|---|---|---|
| **docker-vackup** | Bash script to export/import volumes as tarballs or container images. Simple, no dependencies. | [github.com/BretFisher/docker-vackup](https://github.com/BretFisher/docker-vackup) |
| **loomchild/volume-backup** | Pipe volume contents directly between hosts over SSH in one command. | [github.com/loomchild/volume-backup](https://github.com/loomchild/volume-backup) |
| **offen/docker-volume-backup** | Runs as a sidecar container with cron scheduling, S3/GCS/SSH/WebDAV backends, and pre/post hooks for stopping containers during backup. Best for ongoing automated backups. | [github.com/offen/docker-volume-backup](https://github.com/offen/docker-volume-backup) |

### When to use what

- **One-time migration**: `pg_dump` / `pg_restore` for databases + `docker-vackup` for any other volumes. Simple and reliable.
- **Ongoing backups** (so the next migration is easier): Set up `offen/docker-volume-backup` as a sidecar that ships nightly snapshots to S3 or another remote backend.
- **Moving Coolify itself**: Use Coolify's built-in backup/restore (dashboard or CLI).

### Recommendation for this project

For Arxivian specifically, `pg_dump` / `pg_restore` is the best approach for the databases because:

- It handles pgvector extensions correctly.
- It is format-aware (not just raw file copying).
- It allows selective restore and schema-level control.
- Raw volume copying of Postgres data files risks corruption if the container is not fully stopped or the PG versions differ.

Use the volume-level tools (vackup, offen) only for non-database volumes or as a complement to database-native dumps.
