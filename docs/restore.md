# Restoring a backup

1. On any computer with Docker and rclone: configure the same R2 + crypt remotes (the owner's crypt passwords).
2. `rclone copy r2crypt:inceptiondesign-backups/<YYYY-MM-DD> ./restore/`
   You get `*-database.sql.gz`, `*-files.tar` and `*-private-files.tar`.
3. Start a bench with the same versions (`docs/versions.md`) or the tagged image, with a fresh site.
4. `bench --site <site> restore ./restore/<...>-database.sql.gz --with-public-files ./restore/<...>-files.tar --with-private-files ./restore/<...>-private-files.tar`
5. `bench --site <site> migrate`, then open `/app` and `/portal` and check a recent project and its photos.
6. Record the time it took in `docs/progress/phase-19.md` (acceptance test: a restore on the owner's computer using only this page).
