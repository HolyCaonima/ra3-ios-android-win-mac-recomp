# SPDX-License-Identifier: MIT
# Shared configuration selection; optimization flags remain the caller's choice.
set(RA3_BUILD_PROFILE "release" CACHE STRING "Build profile: dev or release")
set_property(CACHE RA3_BUILD_PROFILE PROPERTY STRINGS dev release)
if(RA3_BUILD_PROFILE STREQUAL "dev")
  set(RA3_PROFILE_CONFIG RelWithDebInfo)
elseif(RA3_BUILD_PROFILE STREQUAL "release")
  set(RA3_PROFILE_CONFIG Release)
else()
  message(FATAL_ERROR "RA3_BUILD_PROFILE must be dev or release, got: ${RA3_BUILD_PROFILE}")
endif()
set(CMAKE_BUILD_TYPE "${RA3_PROFILE_CONFIG}" CACHE STRING "Selected by RA3_BUILD_PROFILE" FORCE)
if(CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_CONFIGURATION_TYPES "${RA3_PROFILE_CONFIG}" CACHE STRING "Selected by RA3_BUILD_PROFILE" FORCE)
endif()
set(RA3_PROFILE_INCLUDE "${CMAKE_CURRENT_BINARY_DIR}/build-profile")
file(MAKE_DIRECTORY "${RA3_PROFILE_INCLUDE}")
configure_file("${CMAKE_CURRENT_LIST_DIR}/build_profile.h.in"
  "${RA3_PROFILE_INCLUDE}/ra3_build_profile.h" @ONLY)
configure_file("${CMAKE_CURRENT_LIST_DIR}/build_profile.json.in"
  "${CMAKE_CURRENT_BINARY_DIR}/ra3-build-profile.json" @ONLY)
message(STATUS "Build profile: ${RA3_BUILD_PROFILE} (${RA3_PROFILE_CONFIG})")

function(ra3_apply_build_profile target)
  target_include_directories(${target} PRIVATE "${RA3_PROFILE_INCLUDE}")
endfunction()
