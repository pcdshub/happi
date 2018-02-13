<h1 align="center">HAPPI</h1>

<div align="center">
  <strong>Heuristic Access to Positioning of Photon Instrumentation</strong>
</div>

<p align="center">
  <a href="#motivation">Motivation</a> •
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#basic-usage">Basic Usage</a> •
</p>

<div align="center">
  <!-- Build Status -->
  <a href="https://travis-ci.org/pcdshub/happi">
    <img
src="https://img.shields.io/travis/pcdshub/happi/master.svg?style=flat-square"
      alt="Build Status" />
  </a>
  <!-- Test Coverage -->
  <a href="https://codecov.io/github/pcdshub/happi">
    <img
src="https://img.shields.io/codecov/c/github/pcdshub/happi/master.svg?style=flat-square"
      alt="Test Coverage" />
  </a>
</div>

## Motivation
LCLS endstations deal with dynamic sets of instrumentation. Information like
ports, triggers and aliases are all important for operation, but hard to manage
when spread across a multitude of applications. **Happi** solves this problem
by creating a single access point for all the metadata required to interface
with LCLS instrumentation. Using a flexible `container` based system Happi
allows the enforcement of specific conventions while still permitting flexible
data entry where required.


## Features
* Manage information for specific device types using containers
* Input arbitrary metadata associated with a specific device
* Flexible backend support for multiple types of databases; MongoDB, JSON e.t.c
* Easily search database entries for device/s that match a set of keys

## Installation

Install the most recent tagged build: `conda install happi -c pcds-tag -c conda-forge`

Install the most recent development build: `conda install happi -c pcds-dev - conda-forge`

## Basic Usage 

The `happi.Client` is your main interface to the underlying device database.
You have the choice of either creating your database backend by hand or using
the environment variable `$HAPPI_BACKEND` to create a persistent reference to
your database type. By default, the `Client` assumes a `JSON` file database:

```python

   import happi

   client = happi.Client(path='path/to/my_db.json')
```

If your database has entries, you should either be able to search by key
variables for individual or multiple devices.

```python

   client.find_device(name="My Device")

   client.search(stand='DG2')
```

Once you have the device you want, you can edit the information just as you
would any other Python object. View the device information in a
convenient table using `.show_info`:

```python

   dev = client.find_device(name="My Device")

   dev.z = 432.1

   dev.show_info()
```
#### Output

```text
+--------------+----------------------+
| EntryInfo    | Value                |
+--------------+----------------------+
| active       | True                 |
| beamline     | LCLS                 |
| name         | My Device            |
| parent       | None                 |
| prefix       | MY:DEV:01            |
| stand        | None                 |
| system       | None                 |
| z            | 432.10000            |
+--------------+----------------------+
```

After you are satisfied with your changes, push the information back to the
database using the `.save` method. If this is a new device, you will have to
call `Client.add_device`. Before the entry is modified in the database, the
`happi.Client` confirms that the new changes meet all the requirements
specified by the container.

```python

   dev.save()
```
