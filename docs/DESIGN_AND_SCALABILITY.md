# Architecture & Scalability Strategy

## 🏗️ High-Level Design

The system implements a **competing consumers pattern** for data ingestion and a **CQRS-inspired separation** (conceptually) between the heavy write operations (ingestion) and high-performance reads (API).

### Core Components

- **Ingestion Engine**: Celery workers running isolated tasks to fetch and normalize data from external providers.
- **Storage**: PostgreSQL with strictly defined schemas to enforce data integrity on "dirty" external inputs.
- **API**: Lightweight Flask application serving read-only traffic, shielded by Redis caching.

## 🧠 Key Engineering Decisions

### 1. Relational Database over NoSQL

**Decision**: PostgreSQL was chosen over MongoDB/NoSQL.
**Reasoning**: Event data is highly structured and relational (Events -> Plans -> Zones). We require strong consistency (ACID) during the complex upsert/sync process to prevent data corruption when updating existing records. JSONB columns can be utilized where schema flexibility is needed, offering the best of both worlds.

### 2. Async Ingestion (Decoupling)

**Decision**: Background synchronization via Celery instead of on-demand fetching.
**Reasoning**: External APIs are unreliable and slow. Decoupling ingestion ensures the internal API **always responds in <50ms**, regardless of the provider's status. It also allows us to control the rate of ingestion independently of user traffic.

### 3. "Atomic" Upsert Strategy

**Decision**: Custom upsert logic combining Python-level diffing and DB-level transactions.
**Reasoning**: We must detect "stale" data (events present in the DB but missing from the latest XML feed) without wiping the database. The system marks records as `last_seen_at` = `now`. Records not updated in the current batch are effectively "invisible" to the API search scope without being physically deleted, allowing for historical auditing.

## ⚖️ Trade-offs & Constraints

- **Pagination**: The current implementation strictly adheres to the provided OpenAPI spec, which did not include pagination parameters. In a real-world V2, pagination (cursor-based) would be mandatory to prevent large payloads.
- **Redis Production Config**: For high-throughput scenarios, the host machine requires `vm.overcommit_memory = 1` to prevent Redis fork failures during background saves. This is documented here as it requires host-level access beyond the container.

## 🚀 Scaling Strategy

### Handling High Read Traffic (10k+ RPS)

- **Multi-Level Caching**:
  - **L1 (Edge)**: CDN for identical queries (e.g., "events this weekend").
  - **L2 (App)**: Redis cache for API responses (TTL 60s).
  - **L3 (DB)**: Read Replicas. The API connects to a read-only replica, while the Celery workers write to the primary.

### Handling Data Volume Growth

- **Batch Processing**: Ingestion happens in batches (e.g., 100 events) to minimize database round-trips.
- **Worker Auto-scaling**: KEDA (Kubernetes Event-driven Autoscaling) can be used to scale Celery workers based on queue depth if we add hundreds of providers.

### Production Readiness Gaps (Future Work)

- **Database Partitioning**: Partitioning the `events` table by `start_date` would significantly speed up range queries as historical data grows.
- **Rate Limiting**: Implementing API rate limiting (Token Bucket) to protect against abuse.
