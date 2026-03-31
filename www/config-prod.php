<?php

require_once('/srv/www/bbsengine6/php/bootstrap.php');
require_once('util.php');
\bbsengine6\util\add_include_paths(['/srv/www/zoid6/php/', '/srv/www/bbsengine6/php/', '/srv/www/smarty/']);

// Define configuration constants in config namespace (required by bbsengine6)
// Using backslash prefix makes them accessible via defined('\config\CONSTANT')
define("config\SITETITLE", "Project Asimov - Robotics, AI, and Augmented Reality");
define("config\SITEURL", "https://zoidtechnologies.com/asimov/");
define("config\SITEDESCRIPTION", "Asimov");
define("config\VHOSTDIR", "/srv/www/vhosts/zoidtechnologies.com/");
define("config\DOCUMENTROOT", \config\VHOSTDIR . "html/asimov/");
define("config\SKINDIR", \config\DOCUMENTROOT . "skin/");
define("config\SKINURL", \config\SITEURL . "skin/");
define("config\JSURL", "/asimov/js/");
define("config\IMAGESURL", "https://zoidtechnologies.com/static/");
define("config\SMARTYCOMPILEDTEMPLATESDIR", \config\VHOSTDIR . "templates_c");
define("config\SMARTYPLUGINSDIR", [ 0 => \config\VHOSTDIR . "smarty/", 1 => "/srv/www/zoid6/smarty/"]);
define("config\SMARTYTEMPLATESDIR", [ 0 => \config\DOCUMENTROOT . "skin/tmpl/", 1=> "/srv/www/zoid6/skin/tmpl/", 2 => "/srv/www/bbsengine6/skin/tmpl/"]);
define("config\LOGENTRYPREFIX", "asimovprod");
define("config\STATICSKINURL", "/static/skin/");
define("config\GOOGLEANALYTICSACCOUNT", "UA-23705021-1");

// Create global aliases for code that references constants directly without namespace
define("SITETITLE", \config\SITETITLE);
define("SITEURL", \config\SITEURL);
define("SITEDESCRIPTION", \config\SITEDESCRIPTION);
define("VHOSTDIR", \config\VHOSTDIR);
define("DOCUMENTROOT", \config\DOCUMENTROOT);
define("SKINDIR", \config\SKINDIR);
define("SKINURL", \config\SKINURL);
define("JSURL", \config\JSURL);
define("IMAGESURL", \config\IMAGESURL);
define("SMARTYTEMPLATESDIR", \config\SMARTYTEMPLATESDIR);
define("SMARTYCOMPILEDTEMPLATESDIR", \config\SMARTYCOMPILEDTEMPLATESDIR);
define("SMARTYPLUGINSDIR", \config\SMARTYPLUGINSDIR);
define("LOGENTRYPREFIX", \config\LOGENTRYPREFIX);
define("STATICSKINURL", \config\STATICSKINURL);

?>
