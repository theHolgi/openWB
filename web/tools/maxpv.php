<?php
$returnPage = "Location: ../index.php";
if (isset($_GET['maxeinspeisungs'])) {
	$result = '';
	$lines = file('/var/www/html/openWB/openwb.conf');
	foreach($lines as $line) {
		$writeit = '0';
		if(strpos($line, "maxuberschuss=") !== false) {
			$result .= 'maxuberschuss='.$_GET['maxeinspeisungs']."\n";
			$writeit = '1';
		}
		if ($writeit == '0') {
			$result .= $line;
		}
	}
	file_put_contents('/var/www/html/openWB/openwb.conf', $result);
}
header($returnPage);
?>