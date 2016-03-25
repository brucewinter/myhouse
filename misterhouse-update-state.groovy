/*
 *  MisterHouse Update State
 
 *  Code: https://github.com/brucewinter/myhouse/blob/master/misterhouse-update-state.groovy
 
 *
 *  Copyright 2014 bruce winter
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 *  in compliance with the License. You may obtain a copy of the License at:
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 *  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License
 *  for the specific language governing permissions and limitations under the License.
 *
 */
definition(
    name: "MisterHouse State Update",
    namespace: "",
    author: "Bruce Winter",
    description: "Sends device state changes to MisterHouse.  Example at http://misterhouse.blogspot.com/2014/10/track-cat.html",
    category: "",
    iconUrl: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience.png",
    iconX2Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png")


preferences
{
    section("Devices...") {
        input "switches", "capability.switch", title: "Which Switches?", multiple: true, required: false
        input "motionSensors", "capability.motionSensor", title: "Which Motion Sensors?", multiple: true, required: false
        input "contactSensors", "capability.contactSensor", title: "Which Contact Sensors?", multiple: true, required: false
        input "presenceSensors", "capability.presenceSensor", title: "Which Presence Sensors?", multiple: true, required: false
        input "accelerationSensors", "capability.accelerationSensor", title: "Which Acceleration Sensors?", multiple: true, required: false
        input "locks", "capability.lock", title: "Which Locks?", multiple: true, required: false
    }
    section("MisterHouse...") {
        input "ip_address", "text", title: "Local MisterHouse ip address", required: false
    }
}

def installed()
{
    log.debug "'MisterHouse' installed with settings: ${settings}"
    initialize()
}

def updated()
{
    log.debug "'MisterHouse' updated with settings: ${settings}"
    unsubscribe()
    initialize()
}

def initialize()
{
    /**
     * You can customize each of these to only receive one type of notification
     * by subscribing only to the individual event for each type. Additional
     * logic would be required in the Preferences section and the device handler.
     */

    if (switches) {
        // switch.on or switch.off
        subscribe(switches, "switch", handler)
    }
    if (motionSensors) {
        // motion.active or motion.inactive
        subscribe(motionSensors, "motion", handler)
    }
    if (contactSensors) {
        // contact.open or contact.closed
        subscribe(contactSensors, "contact", handler)
    }
    if (presenceSensors) {
        // presence.present or 'presence.not present'  (Why the space? It is dumb.)
        subscribe(presenceSensors, "presence", handler)
    }
    if (accelerationSensors) {
        // acceleration.active or acceleration.inactive
        subscribe(accelerationSensors, "acceleration", handler)
    }
    if (locks) {
        // lock.locked or lock.unlocked
        subscribe(locks, "lock", handler)
    }
}

def handler(evt) {
    log.debug "MisterHouse: $evt.displayName is $evt.value"
    def mh_name  = "$evt.displayName"
    def mh_value = "$evt.value"
    mh_name  = mh_name.replaceAll(/ /, '_')
    mh_value = mh_name.replaceAll(/ /, '%20')

    log.debug "MisterHouse: $mh_name  $evt.displayName is $evt.value"
     
	def httpRequest = [method: "GET", path: "/SET?\$${mh_name}?$mh_value", headers: [HOST: "$ip_address", Accept: "*/*"]	]
	sendHubCommand(new physicalgraph.device.HubAction(httpRequest))
 
 }
