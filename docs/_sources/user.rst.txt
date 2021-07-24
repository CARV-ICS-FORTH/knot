User guide
==========

This guide walks you through the various Karvdash screens, starting from user sign up, explaining the available functions.

Sign up and login
-----------------

When you visit the dashboard service with your browser, you are greeted with the login screen.

.. figure:: images/login-screen.png

To create an account, select the "Sign up" option on the main screen and fill in a username, password, and contact email.

.. figure:: images/sign-up-screen.png

Once the account is activated by an administrator, login using your username and password. You can change your password when logged in by clicking on the user icon at the top-right of the screen and selecting "Change password" from the menu. The menu also provides options to report an issue, access this documentation, and logout. If you ever forget your password, please ask an administrator to reset it.

Services screen
---------------

The services screen is accessed by selecting "Services" from the menu on the left. You are presented with a list of running services. Select a service name and you will be taken to the service frontend in a new browser tab. Select the "Actions" button to remove a service.

.. note::
   The service may take some time to initialize. If you select a service name immediately after creation, you may see a proxy error. Just wait for a few seconds and refresh your browser.

.. figure:: images/services-screen.png

To start a new service, click on the respective button on the right. You will be shown a list of available service templates. Choose one and click "Create".

The next screen is where you can define service variables. You can optionally change the service name to one that is easier to remember (if a name is already taken, Karvdash will append random characters). Besides the name, each service template has different variables. When done, click "Create" again, and you will be taken back to the service list, which should contain your new service (a message on the top of the screen will verify that a new service started and provide its name).

Templates screen
----------------

The templates screen is accessed by selecting "Templates" from the menu on the left. You are presented with a list of available service templates. Select a template to download it in YAML format. Select the "Actions" button to delete a template (only user templates can be deleted) or start a service from it.

.. figure:: images/templates-screen.png

To add a new template, click on the respective button on the right. The template file format is described in the :ref:`Service templates` chapter.

Images screen
-------------

.. note::
   Image management is an optional Karvdash feature that may have not been enabled in your deployment.

The images screen is accessed by selecting "Images" from the menu on the left. You are presented with a list of container images in the preconfigured private container registry. Select an image to view available tags.

.. figure:: images/images-screen.png

To add a new image, first upload the saved image in "Files" in ``.tar`` format (using the :ref:`Files screen`). Then, select the "Add image" item from the "Actions" button of that file. You will be asked to provide a name and tag for the new image. Note that you must provide a unique name and tag combination, to avoid overwriting other users' images.

Datasets screen
---------------

.. note::
   Dataset management is an optional Karvdash feature that may have not been enabled in your deployment.

The datasets screen is accessed by selecting "Datasets" from the menu on the left. You are presented with a list of configured datasets. Select a dataset to download its configuration in YAML format. Select the "Actions" button to delete a dataset.

Datasets are mounted in containers under ``/mnt/datasets/<name>``.

.. figure:: images/datasets-screen.png

To add a new dataset, click on the respective button on the right. You will be shown a list of available dataset types. Choose one and click "Add".

The next screen is where you can define the dataset configuration. You can optionally change the dataset name to one that is easier to remember (if a name is already taken, Karvdash will append random characters). Besides the name, each dataset type has different configuration options. When done, click "Add" again, and you will be taken back to the datasets list, which should contain your new dataset (a message on the top of the screen will verify that a new dataset has been added and provide its name).

Files screen
------------

The files screen is accessed by selecting "Files" from the menu on the left. You are presented with a list of folders and files in the respective domain. Change domain ("private" or "shared") by clicking on the corresponding buttons on the upper-right of the screen. The "private" domain contains private user files, while "shared" is common across all users. Any user can add or remove files in "shared".

Select a folder to navigate into that path (the current path is shown above the list), or a file to download it. Select the "Actions" button to download a folder as an archive or delete an object. Respective actions are also available to add templates (ending in ``.template.yaml``) or saved container images (ending in ``.tar``).

Files are mounted in containers under ``/private`` and ``/shared`` respectively.

.. figure:: images/files-screen.png

To add a new folder or upload file(s) at the current path, click on the respective buttons on the right. Note that you can not overwrite an existing folder or file.

.. note::
   The "Files" screen is meant to provide the very basic of file-related operations. Use the notebook environment of the "Zeppelin" service as you would use a shell on a UNIX-based machine to control the filesystem in a more elaborate manner, or create a "File Browser" service for a web-based management interface on a specific folder.

Administration
--------------

.. note::
   The information in this section applies only to administrators.

The "admin" user has access to an additional screen named "Users". Moreover, in the "Images" screen, the administrator has the option to use the "Actions" button to delete an image.

The users screen is accessed by selecting "Users" from the menu on the left. You are presented with a list of users, by username. Each user can be "active", meaning with access to the dashboard and services. Each user can also be promoted to an administrator. The respective actions are available in the menu presented when selecting the "Actions" button. An administrator can edit a user's email, change a user's password, impersonate, and delete a user.

When impersonating another user, the whole interface changes to what the user sees and the user icon at the top-right of the screen darkens to signify "impersonation mode". The user menu provides the option to stop impersonating and return to the original user's view.
