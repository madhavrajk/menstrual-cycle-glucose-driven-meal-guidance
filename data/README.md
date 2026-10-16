# data/

Everything in this folder except this README is gitignored.

- `raw/`: the mcPHASES zip from PhysioNet. Each person downloads their own copy, because
  the data use agreement forbids sharing access.
- `processed/`: outputs of `make step1`, `make cgm`, and `make features`.
- `synthetic/`: fake participants from `make synthetic`. Safe to share; this is the public demo data.

**Recommended:** keep real data outside OneDrive by setting `MCPHASES_HOME=~/mcphases` in
`.env` and putting the zip at `~/mcphases/data/raw/`. Everything here syncs to the cloud.
