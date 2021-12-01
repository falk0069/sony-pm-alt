CC=gcc
EXE=sony-guid-setter

SOURCES=$(wildcard *.c)

CFLAGS=
LDFLAGS=-lusb-1.0

GUID:=$(shell lsusb | awk '/Sony Corp/{print $$6}')

# Docker Vars
DIMG=sony-pm-alt
DIMGTAG=latest
NETWORK=host

IMGDIR=/home/zack/Pictures/raw

.PHONY: build_container get_guid

all: $(EXE) run_container

$(EXE): $(SOURCES)
	$(CC) $(CFLAGS) $(SOURCES) -o $@ $(LDFLAGS)

build_container:
	docker build . -t $(DIMG):$(DIMGTAG)

get_guid:
	echo "Set GUID COMMAND: sudo ./${EXE} -g ${GUID}"

#Needs to be ran manually i.e sudo make set_guid
set_guid:
	./$(EXE) -d -g ${GUID}

clean:
	rm $(EXE)

run_container: build_container
	docker run --name=$(DIMG) --net=$(NETWORK) \
		-v $(IMGDIR):/var/lib/Sony --rm $(DIMG):$(DIMGTAG)
