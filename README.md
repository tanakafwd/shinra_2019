# SHINRA 2019 ( 森羅 2019 )

Tools for
[SHINRA 2019: Wikipedia Structuring Project](http://liat-aip.sakura.ne.jp/%e6%a3%ae%e7%be%85/%e6%a3%ae%e7%be%85wikipedia%e6%a7%8b%e9%80%a0%e5%8c%96%e3%83%97%e3%83%ad%e3%82%b8%e3%82%a7%e3%82%af%e3%83%882019/).

## Usage

### Prerequisites

- [Pipenv](https://pipenv.kennethreitz.org/en/latest/)
- [pyenv](https://github.com/pyenv/pyenv)

### Python Environment Initialization

1. Set up required software. See "[Prerequisites](#prerequisites)".
1. Clone this repository.

    ```shell
    $ git clone https://github.com/tanakafwd/shinra_2019.git
    ```

1. Install dependent Python packages.

    ```shell
    $ cd shinra_2019
    $ pipenv --rm
    $ pipenv sync --dev
    ```

### Dataset Arrangement

1. Initialize your Python environment.
  See "[Python Environment Initialization](#python-environment-initialization)".
1. Make a dataset directory like `~/shinra`.
1. Download dataset zip files from the
  [download page](http://liat-aip.sakura.ne.jp/%E6%A3%AE%E7%BE%85/%E6%A3%AE%E7%BE%85wikipedia%E6%A7%8B%E9%80%A0%E5%8C%96%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%882019/%E6%A3%AE%E7%BE%852019%E3%83%87%E3%83%BC%E3%82%BF%E9%85%8D%E5%B8%83/).
1. Put the dataset zip files to the dataset directory.

    ```
    $ tree ~/shinra
    ~/shinra
    ├── JP-30_20190712.zip
    └── JP-5_20190712.zip
    ```

1. Run the script to arrange the dataset.

    ```shell
    $ pipenv run script/arrange_dataset.py --dataset_dir ~/shinra
    ```

    This script arranges the dataset like the following.

    ```
    $ tree ~/shinra
    ~/shinra
    ├── JP-30_20190712.zip
    ├── JP-5_20190712.zip
    ├── annotation
    │   ├── Airport_dist.json
    │   ├── Airport_dist_for_view.json
    │   ├── Bay_dist.json
    │   ├── Bay_dist_for_view.json
    │   ...
    │
    ├── HTML
    │   ├── Airport
    │   │   ├── 1001711.html
    │   │   ...
    │   ├── Bay
    │   │   ├── 1002651.html
    │   │   ...
    │   ...
    │
    └── PLAIN
        ├── Airport
        │   ├── 1001711.txt
        │   ...
        ├── Bay
        │   ├── 1002651.txt
        │   ...
        ...
    ```

### Dataset Catalog Generation

The output catalogs are
[Here](https://github.com/tanakafwd/shinra_2019_data/tree/master/shinra/catalog).

1. Arrange datasets. See "[Dataset Arrangement](#dataset-arrangement)".
1. Make a dataset catalog directory like `~/shinra/catalog`.
1. Run the script to make catalogs.

    ```shell
    $ pipenv run scripts/make_dataset_catalog.py --dataset_dir ~/shinra --output_dir ~/shinra/catalog
    ```

    This script makes dataset catalogs like the following.
    `summary_catalog.csv` is the summary of all categories.

    ```
    $ tree ~/shinra/catalog
    ~/shinra/catalog
    ├── Airport_catalog.csv
    ├── Bay_catalog.csv
    ...
    └── summary_catalog.csv
    ```

### Dataset Annotation Inspection

1. Arrange datasets. See "[Dataset Arrangement](#dataset-arrangement)".
1. Run the script to inspect annotations.

    ```shell
    $ pipenv run scripts/inspect_dataset_annotation.py --dataset_dir ~/shinra --output_dir ~/shinra/annotation_inspection
    ```

### Dataset Page Inspection

1. Arrange datasets. See "[Dataset Arrangement](#dataset-arrangement)".
1. Run the script to inspect pages.

    ```shell
    $ pipenv run scripts/inspect_dataset_page.py --dataset_dir ~/shinra --output_dir ~/shinra/page_inspection
    ```

## Development

### Unit Tests

```shell
$ pipenv run test
```

### Formatter

```shell
$ pipenv run fmt
```

### Linter

```shell
$ pipenv run vet
```

### Dependent Package Update

```shell
$ pipenv install REQUIRED_PACKAGE
$ pipenv run pipfile2req > requirements.txt
```

## License

This work is released under the [MIT License](LICENSE).
