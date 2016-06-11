#!/usr/bin/perl
use strict;
use Net::MQTT::Simple;
use Time::HiRes qw( time sleep);
$| = 1;

my ($time_start1, $time_start2);

my $server = '192.168.0.150';
my $mqtt1 = Net::MQTT::Simple->new($server);

$mqtt1->subscribe( "mh/speak_send",  \&play_start ); 
$mqtt1->subscribe( "mh/speak_done",  \&play_done  ); 

$mqtt1->run();

sub play_start {
    my ($topic, $msg) = @_;
    $time_start1 = time();
    $time_start2 = '';
    print "\n" . localtime() . " tts t=$topic\n";
}

sub play_done {
    my ($topic, $msg) = @_;
    my ($rroom) = split ' ', $msg;
    $time_start2 = time() unless $time_start2;
    my $time_diff1 = int(1000 * (time() - $time_start1));
    my $time_diff2 = int(1000 * (time() - $time_start2));
    print localtime() . " tts t=$topic rr=$rroom td1=$time_diff1 td2=$time_diff2\n";
}
