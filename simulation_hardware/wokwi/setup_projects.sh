#!/bin/bash
# Copies the common module to all device directories for Wokwi simulation

echo "Setting up Wokwi projects..."

cp -r common infant_tag/
cp -r common mother_tag/
cp -r common gate_reader/
cp -r common gate_terminal/

echo "Done! You can now open each folder in Wokwi."
