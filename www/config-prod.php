<?php

require_once('/srv/www/bbsengine6/php/bootstrap.php');
require_once('util.php');
\bbsengine6\util\add_include_paths(['/srv/www/zoid6/php/', '/srv/www/bbsengine6/php/', '/srv/www/smarty/']);

// Define configuration constants in config namespace (required by bbsengine6)
// Using backslash prefix makes them accessible via defined('\config\CONSTANT')
define("config\SITEADMINEMAIL", "asimov <asimov@projects.zoidtechnologies.com>");
define("config\SITENAME", "asimov");
define("config\SITETITLE", "Project Asimov - Robotics, AI, and Augmented Reality");
define("config\SITEURL", "/asimov/");
define("config\SITEDESCRIPTION", "Asimov");
define("config\VHOSTDIR", "/srv/www/vhosts/zoidtechnologies.com/");
define("config\DOCUMENTROOT", \config\VHOSTDIR . "html/asimov/");
define("config\SKINDIR", \config\DOCUMENTROOT . "skin/");
define("config\SKINURL", \config\SITEURL . "skin/");
define("config\JSURL", "/asimov/skin/js/");
define("config\IMAGESURL", "https://zoidtechnologies.com/static/");

// Define SMARTY* constants before including zoid6config.php so it can create global aliases
// SMARTYTEMPLATESDIR - array with proper precedence
define("config\SMARTYTEMPLATESDIR", [
    0 => \config\SKINDIR . "tmpl/",           // New structure: skin/tmpl/
    1 => \config\DOCUMENTROOT . "tmpl/",      // Legacy structure: tmpl/
    2 => "/srv/www/zoid6/shared/skin/tmpl/",  // Shared zoid6 templates (use this first)
    3 => "/srv/www/zoid6/skin/tmpl/",         // zoid6 project templates
    4 => "/srv/www/bbsengine6/skin/tmpl/"    // bbsengine6 framework templates
]);

// SMARTYCOMPILEDTEMPLATESDIR - compiled template cache directory
define("config\SMARTYCOMPILEDTEMPLATESDIR", \config\VHOSTDIR . "templates_c");

// SMARTYPLUGINSDIR - plugin directories for custom Smarty functions and modifiers
define("config\SMARTYPLUGINSDIR", [
    0 => \config\VHOSTDIR . "smarty/",
    1 => "/srv/www/zoid6/smarty/"
]);

// Define URL constants BEFORE zoid6config.php so they're available for templates
define("config\SHAREDSKINURL", "/shared/skin/");
define("config\ENGINESKINURL", "/engine/skin/");
define("config\ENGINEURL", "/engine/");

// Now include zoid6config.php to create global aliases
require_once('zoid6config.php');

define("config\LOGENTRYPREFIX", "asimovprod");
define("config\GOOGLEANALYTICSACCOUNT", "UA-23705021-1");
define("config\SECTIONTEMPLATEDIR", \config\SKINDIR . "tmpl/sections/");

// Create global aliases for non-SMARTY constants
// (SMARTY* aliases are created by zoid6config.php)
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
define("SHAREDSKINURL", \config\SHAREDSKINURL);
define("ENGINESKINURL", \config\ENGINESKINURL);

?>
