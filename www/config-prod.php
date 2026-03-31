<?php

require_once('/srv/www/bbsengine6/php/bootstrap.php');
require_once('util.php');
\bbsengine6\util\add_include_paths(['/srv/www/zoid6/php/', '/srv/www/bbsengine6/php/', '/srv/www/smarty/']);
require_once('zoid6config.php');

// Define configuration constants in config namespace (required by bbsengine6)
// Using backslash prefix makes them accessible via defined('\config\CONSTANT')
define("config\SITEADMINEMAIL", "asimov <asimov@projects.zoidtechnologies.com>");
define("config\SITETITLE", "Project Asimov - Robotics, AI, and Augmented Reality");
define("config\SITEURL", "/asimov/");
define("config\SITEDESCRIPTION", "Asimov");
define("config\VHOSTDIR", "/srv/www/vhosts/zoidtechnologies.com/");
define("config\DOCUMENTROOT", \config\VHOSTDIR . "html/asimov/");
define("config\SKINDIR", \config\DOCUMENTROOT . "skin/");
define("config\SKINURL", \config\SITEURL . "skin/");
define("config\JSURL", "/asimov/skin/js/");
define("config\IMAGESURL", "https://zoidtechnologies.com/static/");

// SMARTYTEMPLATESDIR - 3-element array with proper precedence
// Search order: 1) Site-specific templates 2) bbsengine6 shared 3) zoid6 shared
if (!defined("config\SMARTYTEMPLATESDIR")) {
    define("config\SMARTYTEMPLATESDIR", [
        0 => \config\SKINDIR . "tmpl/",
        1 => "/srv/www/bbsengine6/skin/tmpl/",
        2 => "/srv/www/zoid6/skin/tmpl/"
    ]);
}

// SMARTYCOMPILEDTEMPLATESDIR - compiled template cache directory
if (!defined("config\SMARTYCOMPILEDTEMPLATESDIR")) {
    define("config\SMARTYCOMPILEDTEMPLATESDIR", \config\VHOSTDIR . "templates_c");
}

// SMARTYPLUGINSDIR - plugin directories for custom Smarty functions and modifiers
if (!defined("config\SMARTYPLUGINSDIR")) {
    define("config\SMARTYPLUGINSDIR", [
        0 => \config\VHOSTDIR . "smarty/",
        1 => "/srv/www/zoid6/smarty/"
    ]);
}

define("config\LOGENTRYPREFIX", "asimovprod");
define("config\ENGINEURL", "/engine/");
define("config\GOOGLEANALYTICSACCOUNT", "UA-23705021-1");
define("config\SECTIONTEMPLATEDIR", \config\SKINDIR . "tmpl/sections/");
define("config\STATICSKINURL", "/static/skin/");

// Create global aliases for code that references constants directly without namespace
define("SITEURL", \config\SITEURL);
define("VHOSTDIR", \config\VHOSTDIR);
define("DOCUMENTROOT", \config\DOCUMENTROOT);
define("SKINDIR", \config\SKINDIR);
define("SKINURL", \config\SKINURL);
define("JSURL", \config\JSURL);
define("ENGINEURL", \config\ENGINEURL);
define("IMAGESURL", \config\IMAGESURL);
define("LOGENTRYPREFIX", \config\LOGENTRYPREFIX);
define("SECTIONTEMPLATEDIR", \config\SECTIONTEMPLATEDIR);
define("STATICSKINURL", \config\STATICSKINURL);
define("SMARTYTEMPLATESDIR", \config\SMARTYTEMPLATESDIR);
define("SMARTYCOMPILEDTEMPLATESDIR", \config\SMARTYCOMPILEDTEMPLATESDIR);
define("SMARTYPLUGINSDIR", \config\SMARTYPLUGINSDIR);

?>
