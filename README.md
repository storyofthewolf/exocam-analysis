# analysis

Analysis of small batches of CESM/ExoCAM equilibrium climate simulations.
For timeseries analysis see the `trend` package.
https://github.com/storyofthewolf/trend

## Dependencies
- [`exocampy_tools.py`](https://github.com/storyofthewolf/ExoCAM/blob/main/tools/py_progs/exocampy_tools.py)

## Usage
```bash
python run_analysis.py [options]
```
Reads in list of files defined in `files.in`

| Option | Description |
|--------|-------------|
| `--quiet` | do not print to screen |
| `--printdata` | print output text files |
| `--vert` | calculate vertical profiles |
| `--synch` | calculate substellar/antistellar means |
| `--cf` | tabulate clear sky fluxes and cloud forcings |
| `--nostrout` | remove string type from output text file |


## Notes
- [March, 23, 2026] added global mean vertical profile plotting 
